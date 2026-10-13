from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from auth.constants import UserRole
from auth.crud import (
    create_user_session,
    get_session_computing_id,
    get_session_user,
    get_site_user_by_computing_id,
    get_user_roles,
)
from auth.tables import SiteUserDB, SiteUserRoleDB, UserSessionDB
from database import DBSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def access_client(db_session: DBSession, admin_client: AsyncClient):
    response = await admin_client.get("/auth/user")
    assert response.status_code == status.HTTP_200_OK
    uid = UUID(response.json()["uid"])
    db_session.add(SiteUserRoleDB(uid=uid, role=UserRole.ACCESS, added_by=uid))
    await db_session.commit()
    yield admin_client


async def test__user_endpoints_use_public_uid(db_session: DBSession, access_client: AsyncClient):
    response = await access_client.post("/api/user", json={"computing_id": "uidtarget"})
    assert response.status_code == status.HTTP_201_CREATED
    uid = response.json()["uid"]
    assert UUID(uid).version == 4

    db_user = await get_site_user_by_computing_id(db_session, "uidtarget")
    assert db_user is not None
    assert str(db_user.uid) == uid
    assert await db_session.get(SiteUserDB, UUID(uid)) is db_user

    list_response = await access_client.get("/api/user")
    assert list_response.status_code == status.HTTP_200_OK
    assert any(user["uid"] == uid for user in list_response.json())

    update_response = await access_client.put(f"/api/user/{uid}", json={"roles": ["user"]})
    assert update_response.status_code == status.HTTP_200_OK
    assert update_response.json()["uid"] == uid
    assert update_response.json()["roles"] == ["user"]

    clear_response = await access_client.put(f"/api/user/{uid}", json={"roles": []})
    assert clear_response.status_code == status.HTTP_200_OK
    delete_response = await access_client.delete(f"/api/user/{uid}")
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert delete_response.content == b""

    repeated_delete = await access_client.delete(f"/api/user/{uid}")
    assert repeated_delete.status_code == status.HTTP_404_NOT_FOUND


async def test__user_endpoints_reject_computing_id_paths(access_client: AsyncClient):
    update_response = await access_client.put("/api/user/uidtarget", json={"roles": []})
    delete_response = await access_client.delete("/api/user/uidtarget")
    assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert delete_response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test__update_user_returns_not_found_for_unknown_uid(access_client: AsyncClient):
    response = await access_client.put(f"/api/user/{uuid4()}", json={"roles": []})
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test__update_user_requires_access_role(admin_client: AsyncClient):
    response = await admin_client.put(f"/api/user/{uuid4()}", json={"roles": []})
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test__user_uid_is_stable_across_logins(db_session: DBSession):
    await create_user_session(db_session, "first-uid-session", "uidlogin")
    await db_session.flush()
    user = await get_site_user_by_computing_id(db_session, "uidlogin")
    assert user is not None
    original_uid = user.uid
    assert original_uid.version == 4

    await create_user_session(db_session, "second-uid-session", "uidlogin")
    await db_session.flush()
    await db_session.refresh(user)
    assert user.uid == original_uid


async def test__new_users_have_distinct_uids(db_session: DBSession):
    first = SiteUserDB(computing_id="uidfirst")
    second = SiteUserDB(computing_id="uidsecond")
    db_session.add_all([first, second])
    await db_session.flush()
    assert first.uid.version == second.uid.version == 4
    assert first.uid != second.uid


async def test__users_without_computing_ids_have_independent_primary_keys(db_session: DBSession):
    first = SiteUserDB(computing_id=None)
    second = SiteUserDB(computing_id=None)
    db_session.add_all([first, second])
    await db_session.flush()
    assert first.uid != second.uid
    assert await db_session.get(SiteUserDB, first.uid) is first
    assert await db_session.get(SiteUserDB, second.uid) is second


async def test__auth_references_survive_computing_id_change(db_session: DBSession):
    session_hash = await create_user_session(db_session, "uid-reference-session", "uidoriginal")
    user = await get_site_user_by_computing_id(db_session, "uidoriginal")
    assert user is not None
    uid = user.uid
    db_session.add(SiteUserRoleDB(uid=uid, role=UserRole.USER, added_by=uid))
    await db_session.flush()

    user.computing_id = "uidrenamed"
    await db_session.flush()

    session = await db_session.get(UserSessionDB, session_hash)
    assert session is not None and session.uid == uid
    session_user = await get_session_user(db_session, "uid-reference-session")
    assert session_user is not None
    assert session_user.uid == uid
    assert session_user.computing_id == "uidrenamed"
    assert session_user.roles == frozenset({UserRole.USER})
    assert await get_session_computing_id(db_session, "uid-reference-session") == "uidrenamed"
    roles = await get_user_roles(db_session, uid)
    assert len(roles) == 1
    assert roles[0].uid == roles[0].added_by == uid


async def test__create_user_roles_reference_user_and_admin_uids(db_session: DBSession, admin_client: AsyncClient):
    admin_response = await admin_client.get("/auth/user")
    assert admin_response.status_code == status.HTTP_200_OK
    admin_uid = UUID(admin_response.json()["uid"])
    response = await admin_client.post("/api/user", json={"computing_id": "uidwithroles", "roles": ["user"]})
    assert response.status_code == status.HTTP_201_CREATED
    uid = UUID(response.json()["uid"])
    assignment = await db_session.get(SiteUserRoleDB, (uid, UserRole.USER))
    assert assignment is not None
    assert assignment.uid == uid
    assert assignment.added_by == admin_uid
