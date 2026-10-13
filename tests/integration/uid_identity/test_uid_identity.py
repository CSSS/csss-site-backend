from datetime import UTC, date, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import get_session_user, get_site_user_by_computing_id
from auth.tables import SiteUserDB, SiteUserRoleDB, UserSessionDB
from dependencies import authenticated_user_id, optional_user_id, perm_admin
from officers.constants import OfficerPositionTypeEnum
from officers.crud import get_officer_info
from officers.tables import OfficerInfoDB, OfficerPositionDB, OfficerPositionVersionDB

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test__session_identity_survives_computing_id_changes(db_session: AsyncSession, client: AsyncClient):
    uid = uuid4()
    user = SiteUserDB(uid=uid, computing_id=None)
    db_session.add(user)
    await db_session.flush()
    db_session.add_all(
        [
            SiteUserRoleDB(uid=uid, role=UserRole.ADMIN),
            UserSessionDB(
                session_hash=sha256(b"uid-session").digest(),
                uid=uid,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            ),
        ]
    )
    await db_session.commit()
    client.cookies.set(COOKIE_SESSION_KEY, "uid-session")

    for computing_id in (None, "uidoriginal", "uidrenamed", None):
        user.computing_id = computing_id
        await db_session.commit()
        identity = await get_session_user(db_session, "uid-session")
        assert identity is not None
        assert identity.computing_id == computing_id
        assert identity.roles == frozenset({UserRole.ADMIN})
        assert optional_user_id(identity) == authenticated_user_id(identity) == perm_admin(identity) == uid
        response = await client.get("/auth/user")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["uid"] == str(uid)
        assert response.json()["computing_id"] == computing_id
        # Exercise the standard role dependency through a protected route.
        assert (await client.get("/api/user")).status_code == status.HTTP_200_OK


async def test__missing_and_expired_sessions_have_no_identity(db_session: AsyncSession, client: AsyncClient):
    assert await get_session_user(db_session, "missing") is None
    user = SiteUserDB(computing_id=None)
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserSessionDB(
            session_hash=sha256(b"expired").digest(),
            uid=user.uid,
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    await db_session.commit()
    assert await get_session_user(db_session, "expired") is None
    for session_id in ("missing", "expired"):
        client.cookies.set(COOKIE_SESSION_KEY, session_id)
        assert (await client.get("/api/user")).status_code == status.HTTP_401_UNAUTHORIZED


async def test__standard_admin_dependencies_record_uid_without_computing_id(
    db_session: AsyncSession,
    admin_client: AsyncClient,
):
    admin = await get_site_user_by_computing_id(db_session, "uidadmin")
    assert admin is not None
    admin_uid = admin.uid
    admin.computing_id = None
    await db_session.commit()
    response = await admin_client.post("/api/user", json={"computing_id": "target", "roles": ["user"]})
    assert response.status_code == status.HTTP_201_CREATED
    uid = UUID(response.json()["uid"])
    assignment = await db_session.get(SiteUserRoleDB, (uid, UserRole.USER))
    assert assignment is not None and assignment.added_by == admin_uid
    response = await admin_client.put(f"/api/user/{uid}", json={"roles": ["exec"]})
    assert response.status_code == status.HTTP_200_OK
    assignment = await db_session.get(SiteUserRoleDB, (uid, UserRole.EXEC))
    assert assignment is not None and assignment.added_by == admin_uid


async def test__officers_keep_computing_id_reference_and_set_null(
    db_session: AsyncSession,
    admin_client: AsyncClient,
):
    position = OfficerPositionDB(position="Test officer")
    db_session.add(position)
    await db_session.flush()
    version = OfficerPositionVersionDB(
        position_id=position.id,
        type=OfficerPositionTypeEnum.APPOINTED_REP,
        multiple_allowed=None,
        effective_from=date(2020, 1, 1),
    )
    db_session.add(version)
    await db_session.flush()
    version_id = version.id
    await db_session.commit()
    response = await admin_client.post(
        "/api/officer",
        json=[
            {
                "computing_id": "officerid",
                "legal_name": "Test Officer",
                "position_version_id": version_id,
                "start_date": "2026-01-01",
            }
        ],
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["computing_id"] == "officerid"
    officer = await get_officer_info(db_session, "officerid")
    user = await get_site_user_by_computing_id(db_session, "officerid")
    assert officer is not None and user is not None
    response = await admin_client.get("/api/officer/private")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["computing_id"] == "officerid"
    column = OfficerInfoDB.__table__.c.computing_id
    foreign_key = next(iter(column.foreign_keys))
    assert column.nullable and column.unique
    assert foreign_key.target_fullname == "site_user.computing_id"
    assert foreign_key.ondelete == "SET NULL"
    assert SiteUserDB.__table__.c.computing_id.unique
    user_uid = user.uid
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(SiteUserDB(computing_id="officerid"))
            await db_session.flush()
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            db_session.add(OfficerInfoDB(computing_id="officerid", legal_name="Duplicate"))
            await db_session.flush()
    await db_session.execute(delete(SiteUserDB).where(SiteUserDB.uid == user_uid))
    await db_session.flush()
    await db_session.refresh(officer)
    assert officer.computing_id is None
    assert officer.legal_name == "Test Officer"
