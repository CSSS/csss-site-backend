from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import create_user_session, get_site_user_by_computing_id
from auth.tables import SiteUserDB, SiteUserRoleDB
from constants import TZ_INFO
from officers.constants import OfficerPositionTypeEnum
from officers.crud import (
    create_multiple_officers,
    get_active_officer_terms,
    get_officer_info,
    get_officer_term_by_id,
    get_officer_terms,
)
from officers.models import OfficerCreate
from officers.tables import OfficerInfoDB, OfficerPositionDB, OfficerPositionVersionDB, OfficerTermDB

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def log_in(client: AsyncClient, db_session: AsyncSession, role: UserRole):
    session_id = f"officer-test-{role.value}"
    computing_id = f"test{role.value}"
    await create_user_session(db_session, session_id, computing_id)
    user = await get_site_user_by_computing_id(db_session, computing_id)
    assert user is not None
    db_session.add(SiteUserRoleDB(uid=user.uid, role=role))
    await db_session.commit()
    client.cookies.set(COOKIE_SESSION_KEY, session_id, domain="test.local", path="/")


@pytest_asyncio.fixture(loop_scope="session")
async def admin_client(client: AsyncClient, db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    await log_in(client, db_session, UserRole.ADMIN)
    yield client


@pytest.fixture
def today() -> date:
    return datetime.now(TZ_INFO).date()


async def add_position(
    db_session: AsyncSession,
    name: str = "Test representative",
    *,
    position_type: OfficerPositionTypeEnum = OfficerPositionTypeEnum.APPOINTED_REP,
    multiple_allowed: bool | None = None,
    effective_from: date = date(2020, 1, 1),
    effective_to: date | None = None,
) -> int:
    position = OfficerPositionDB(position=name)
    db_session.add(position)
    await db_session.flush()
    version = OfficerPositionVersionDB(
        position_id=position.id,
        type=position_type,
        multiple_allowed=multiple_allowed,
        effective_from=effective_from,
        effective_to=effective_to,
    )
    db_session.add(version)
    await db_session.flush()
    return version.id


async def add_term(
    db_session: AsyncSession,
    version_id: int,
    start: date,
    end: date | None = None,
    *,
    computing_id: str = "officer1",
) -> int:
    terms = await create_multiple_officers(
        db_session,
        [
            OfficerCreate(
                computing_id=computing_id,
                legal_name=f"Officer {computing_id}",
                preferred_name="Test",
                position_version_id=version_id,
                start_date=start,
                end_date=end,
                phone_number="6045550100",
                discord_id=str(int.from_bytes(computing_id.encode(), "big")),
                google_drive_email="officer@example.test",
                github_username="officer-test",
                photo_url="https://example.test/officer.jpg",
            )
        ],
    )
    return terms[0].id


async def test__officer_tables_start_empty(db_session: AsyncSession, client: AsyncClient):
    for model in (
        OfficerInfoDB,
        OfficerPositionDB,
        OfficerPositionVersionDB,
        OfficerTermDB,
    ):
        assert await db_session.scalar(select(func.count()).select_from(model)) == 0
    assert (await client.get("/api/officer")).json() == []
    assert (await client.get("/api/officer/position")).json() == []


async def test__read_active_and_all_terms(db_session: AsyncSession, today: date):
    assert await get_active_officer_terms(db_session) == []
    version_id = await add_position(db_session)
    historical = await add_term(db_session, version_id, today - timedelta(days=20), today - timedelta(days=1))
    active = await add_term(db_session, version_id, today - timedelta(days=1), today)
    ongoing = await add_term(db_session, version_id, today, computing_id="officer2")
    future = await add_term(db_session, version_id, today + timedelta(days=1), computing_id="officer3")
    assert {term.id for term in await get_active_officer_terms(db_session)} == {active, ongoing}
    assert {term.id for term in await get_officer_terms(db_session, False)} == {historical, active, ongoing}
    assert {term.id for term in await get_officer_terms(db_session, True)} == {historical, active, ongoing, future}
    assert await get_officer_term_by_id(db_session, future) is not None
    assert await get_officer_term_by_id(db_session, future + 1) is None
    info = await get_officer_info(db_session, "officer1")
    assert info is not None and info.legal_name == "Officer officer1"
    assert await get_officer_info(db_session, "unknown") is None


@pytest.mark.parametrize("current", [False, True])
async def test__public_officers_filter_dates_and_hide_private_data(
    db_session: AsyncSession,
    client: AsyncClient,
    today: date,
    current: bool,
):
    version_id = await add_position(db_session, "Representative")
    await add_term(db_session, version_id, today - timedelta(days=20), today - timedelta(days=1))
    await add_term(db_session, version_id, today, computing_id="officer2")
    await add_term(db_session, version_id, today + timedelta(days=1), computing_id="officer3")
    await db_session.commit()
    response = await client.get("/api/officer", params={"current": current})
    assert response.status_code == status.HTTP_200_OK
    terms = response.json()
    assert len(terms) == (1 if current else 2)
    assert all(term["position"] == "Representative" for term in terms)
    assert all(
        set(term)
        == {
            "legal_name",
            "preferred_name",
            "start_date",
            "end_date",
            "position",
            "photo_url",
        }
        for term in terms
    )
    assert all(term["photo_url"] == "https://example.test/officer.jpg" for term in terms)


@pytest.mark.parametrize("role", [UserRole.EXEC, UserRole.ADMIN, UserRole.ACCESS])
@pytest.mark.parametrize("current", [False, True])
async def test__private_officers_include_current_fields(
    db_session: AsyncSession,
    client: AsyncClient,
    today: date,
    role: UserRole,
    current: bool,
):
    version_id = await add_position(db_session)
    active_id = await add_term(db_session, version_id, today)
    future_id = await add_term(db_session, version_id, today + timedelta(days=1), computing_id="officer2")
    await log_in(client, db_session, role)
    response = await client.get("/api/officer/private", params={"current": current})
    assert response.status_code == status.HTTP_200_OK
    terms = response.json()
    assert {term["term_id"] for term in terms} == ({active_id} if current else {active_id, future_id})
    assert all(term["position_version_id"] == version_id for term in terms)
    assert all(term["computing_id"] in {"officer1", "officer2"} for term in terms)
    assert all(term["phone_number"] == "6045550100" for term in terms)
    assert all(term["discord_id"] == str(int.from_bytes(term["computing_id"].encode(), "big")) for term in terms)
    assert all(term["github_username"] == "officer-test" for term in terms)
    assert all(term["google_drive_email"] == "officer@example.test" for term in terms)
    assert all("nickname" not in term and "discord_name" not in term for term in terms)


async def test__public_admin_listing_includes_future_terms(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
):
    version_id = await add_position(db_session)
    await add_term(db_session, version_id, today + timedelta(days=1))
    await db_session.commit()
    response = await admin_client.get("/api/officer")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert "computing_id" not in response.json()[0]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/officer/private", None),
        ("POST", "/api/officer", []),
        ("PATCH", "/api/officer/term/1", {"info": {"legal_name": "Updated"}}),
        ("DELETE", "/api/officer/term/1", None),
        ("POST", "/api/officer/position", {}),
        ("POST", "/api/officer/position/1", {}),
        ("PATCH", "/api/officer/position/1", {"effective_to": None}),
    ],
)
@pytest.mark.parametrize("role", [None, UserRole.USER])
async def test__officer_routes_require_permission(
    client: AsyncClient,
    db_session: AsyncSession,
    method: str,
    path: str,
    body: dict | list | None,
    role: UserRole | None,
):
    if role is not None:
        await log_in(client, db_session, role)
    response = await client.request(method, path, json=body)
    assert response.status_code == (status.HTTP_401_UNAUTHORIZED if role is None else status.HTTP_403_FORBIDDEN)


async def test__admin_create_officers_reuses_site_user_and_officer_info(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
):
    version_id = await add_position(db_session)
    existing_user = SiteUserDB(computing_id="officer1")
    db_session.add(existing_user)
    await db_session.flush()
    uid = existing_user.uid
    await db_session.commit()
    body = {
        "computing_id": "officer1",
        "legal_name": "Test Officer",
        "preferred_name": "Test",
        "position_version_id": version_id,
        "start_date": today.isoformat(),
    }
    response = await admin_client.post("/api/officer", json=[body])
    assert response.status_code == status.HTTP_200_OK
    first = response.json()[0]
    assert first["computing_id"] == "officer1"
    assert first["position_version_id"] == version_id
    assert first["legal_name"] == "Test Officer"
    assert first["preferred_name"] == "Test"
    response = await admin_client.post(
        "/api/officer", json=[{**body, "start_date": (today + timedelta(days=1)).isoformat()}]
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["term_id"] != first["term_id"]
    db_session.expire_all()
    user = await get_site_user_by_computing_id(db_session, "officer1")
    assert user is not None and user.uid == uid
    assert await db_session.scalar(select(func.count()).select_from(OfficerInfoDB)) == 1
    assert await db_session.scalar(select(func.count()).select_from(OfficerTermDB)) == 2


async def test__admin_create_new_officer_creates_uid_user(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
):
    version_id = await add_position(db_session)
    await db_session.commit()
    response = await admin_client.post(
        "/api/officer",
        json=[
            {
                "computing_id": "newuser",
                "legal_name": "New Officer",
                "position_version_id": version_id,
                "start_date": today.isoformat(),
            }
        ],
    )
    assert response.status_code == status.HTTP_200_OK
    user = await get_site_user_by_computing_id(db_session, "newuser")
    assert user is not None and user.uid.version == 4
    assert await get_officer_info(db_session, "newuser") is not None


@pytest.mark.parametrize(
    "body",
    [
        {"info": {"legal_name": "Updated", "phone_number": None}},
        {"term": {"photo_url": None}},
        {"info": {"preferred_name": "Preferred"}, "term": {"end_date": None}},
    ],
)
async def test__admin_patch_officer_info_and_term(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
    body: dict,
):
    version_id = await add_position(db_session)
    target = await add_term(db_session, version_id, today, today + timedelta(days=10))
    other = await add_term(db_session, version_id, today, computing_id="officer2")
    await db_session.commit()
    original = (await admin_client.get("/api/officer/private")).json()
    original_other = next(term for term in original if term["term_id"] == other)
    original_target = next(term for term in original if term["term_id"] == target)
    response = await admin_client.patch(f"/api/officer/term/{target}", json=body)
    assert response.status_code == status.HTTP_200_OK
    expected = {**original_target, **body.get("info", {}), **body.get("term", {})}
    assert response.json() == expected
    terms = (await admin_client.get("/api/officer/private")).json()
    assert next(term for term in terms if term["term_id"] == target) == expected
    assert next(term for term in terms if term["term_id"] == other) == original_other


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"info": {"legal_name": None}},
        {"info": {"legal_name": " "}},
        {"term": {"start_date": None}},
        {"term": {"position_version_id": None}},
        {"term": {"start_date": "2026-02-02", "end_date": "2026-02-01"}},
    ],
)
async def test__admin_patch_rejects_invalid_fields(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
    body: dict,
):
    version_id = await add_position(db_session)
    term_id = await add_term(db_session, version_id, today)
    await db_session.commit()
    response = await admin_client.patch(f"/api/officer/term/{term_id}", json=body)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test__admin_patch_missing_term(admin_client: AsyncClient):
    response = await admin_client.patch("/api/officer/term/1", json={"info": {"legal_name": "Updated"}})
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test__admin_delete_term_preserves_other_terms_and_officer(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
):
    version_id = await add_position(db_session)
    target = await add_term(db_session, version_id, today)
    other = await add_term(db_session, version_id, today + timedelta(days=1))
    await db_session.commit()
    response = await admin_client.delete(f"/api/officer/term/{target}")
    assert response.status_code == status.HTTP_204_NO_CONTENT and response.content == b""
    assert await get_officer_term_by_id(db_session, target) is None
    assert await get_officer_term_by_id(db_session, other) is not None
    assert await get_officer_info(db_session, "officer1") is not None


async def test__officer_reference_set_null_on_user_deletion(db_session: AsyncSession, today: date):
    version_id = await add_position(db_session)
    await add_term(db_session, version_id, today)
    info = await get_officer_info(db_session, "officer1")
    assert info is not None
    await db_session.execute(delete(SiteUserDB).where(SiteUserDB.computing_id == "officer1"))
    await db_session.flush()
    await db_session.refresh(info)
    assert info.computing_id is None
    assert info.legal_name == "Officer officer1"


async def test__admin_create_position_and_list_versions(admin_client: AsyncClient, today: date):
    response = await admin_client.post(
        "/api/officer/position",
        json={
            "name": "Representative",
            "type": "appointed_representative",
            "multiple_allowed": None,
            "effective_from": today.isoformat(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    position = response.json()
    assert position["position_id"] > 0 and position["version_id"] > 0
    assert position["name"] == "Representative"
    assert (await admin_client.get("/api/officer/position")).json() == [position]
    assert (await admin_client.get("/api/officer/position?active=true")).json() == [position]
    response = await admin_client.post(
        "/api/officer/position",
        json={
            "name": " representative ",
            "type": "appointed_representative",
            "effective_from": today.isoformat(),
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT


async def test__admin_create_position_version_closes_previous(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
):
    version_id = await add_position(db_session)
    version = await db_session.get(OfficerPositionVersionDB, version_id)
    assert version is not None
    position_id = version.position_id
    await db_session.commit()
    start = today + timedelta(days=1)
    response = await admin_client.post(
        f"/api/officer/position/{position_id}",
        json={
            "type": "appointed_representative",
            "effective_from": start.isoformat(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["position_id"] == position_id
    assert response.json()["version_id"] != version_id
    await db_session.refresh(version)
    assert version.effective_to == today
    assert (await admin_client.get("/api/officer/position")).json() == [response.json()]


async def test__admin_create_version_for_missing_position(admin_client: AsyncClient, today: date):
    response = await admin_client.post(
        "/api/officer/position/1",
        json={
            "type": "appointed_representative",
            "effective_from": today.isoformat(),
        },
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test__admin_mark_position_inactive(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
):
    version_id = await add_position(db_session, effective_from=today - timedelta(days=10))
    version = await db_session.get(OfficerPositionVersionDB, version_id)
    assert version is not None
    position_id = version.position_id
    await db_session.commit()
    end = today - timedelta(days=1)
    response = await admin_client.patch(f"/api/officer/position/{position_id}", json={"effective_to": end.isoformat()})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["effective_to"] == end.isoformat()
    assert (await admin_client.get("/api/officer/position?active=true")).json() == []


@pytest.mark.parametrize("violation", ["outside_version", "executive_overlap", "single_holder"])
async def test__officer_database_triggers_reject_invalid_terms(
    db_session: AsyncSession,
    today: date,
    violation: str,
):
    version_id = await add_position(
        db_session,
        position_type=OfficerPositionTypeEnum.EXECUTIVE,
        multiple_allowed=violation != "single_holder",
        effective_from=today,
    )
    if violation != "outside_version":
        await add_term(db_session, version_id, today)
    with pytest.raises(IntegrityError) as error:
        async with db_session.begin_nested():
            if violation == "outside_version":
                await add_term(db_session, version_id, today - timedelta(days=1))
            elif violation == "executive_overlap":
                other_version = await add_position(
                    db_session,
                    "Second executive",
                    position_type=OfficerPositionTypeEnum.EXECUTIVE,
                    multiple_allowed=True,
                )
                await add_term(db_session, other_version, today)
            else:
                await add_term(db_session, version_id, today, computing_id="officer2")
    assert getattr(error.value.orig, "sqlstate", None) == "23514"


async def test__admin_patch_reassigns_position_and_dates(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    today: date,
):
    original_version = await add_position(db_session, "Original position")
    new_version = await add_position(db_session, "New position")
    term_id = await add_term(db_session, original_version, today)
    await db_session.commit()
    update = {
        "position_version_id": new_version,
        "start_date": (today - timedelta(days=1)).isoformat(),
        "end_date": (today + timedelta(days=10)).isoformat(),
    }
    response = await admin_client.patch(f"/api/officer/term/{term_id}", json={"term": update})
    assert response.status_code == status.HTTP_200_OK
    assert all(response.json()[key] == value for key, value in update.items())
    response = await admin_client.get("/api/officer")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()[0]["position"] == "New position"
    assert response.json()[0]["start_date"] == update["start_date"]
    assert response.json()[0]["end_date"] == update["end_date"]


@pytest.mark.parametrize(
    "body",
    [
        {"computing_id": "officer1", "legal_name": "Test Officer", "start_date": "2026-01-01"},
        {"computing_id": "", "legal_name": "Test Officer", "position_version_id": 1, "start_date": "2026-01-01"},
        {
            "computing_id": "officer1",
            "legal_name": "Test Officer",
            "position_version_id": 1,
            "start_date": "2026-01-02",
            "end_date": "2026-01-01",
        },
    ],
)
async def test__admin_create_officer_rejects_invalid_payload(admin_client: AsyncClient, body: dict):
    response = await admin_client.post("/api/officer", json=[body])
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
