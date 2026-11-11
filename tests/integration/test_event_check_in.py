from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import create_user_session, get_site_user_by_computing_id
from auth.tables import SiteUserRoleDB
from event.constants import EventStatusEnum
from event.tables import EventDB
from event_check_in.tables import EventCheckInDB

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="session"),
]


@pytest_asyncio.fixture(loop_scope="session")
async def event_eid(db_session: AsyncSession):
    start = datetime(2030, 1, 1, 17, tzinfo=UTC)
    event = EventDB(
        name="Check-in test event",
        description="Event for check-in integration tests.",
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        status=EventStatusEnum.SCHEDULED,
    )
    db_session.add(event)
    await db_session.flush()
    eid = event.eid
    await db_session.commit()
    return eid


@pytest_asyncio.fixture(loop_scope="session")
async def check_in(admin_client: AsyncClient, event_eid: str):
    response = await admin_client.post(
        f"/api/event/{event_eid}/check-in",
        json={
            "name": "Main check-in",
            "enabled": True,
            "opens_at": "2030-01-01T17:00:00Z",
            "closes_at": "2030-01-01T18:00:00Z",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_check_in_create_read_update_and_delete(
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
):
    collection = f"/api/event/{event_eid}/check-in"
    individual = f"{collection}/{check_in['id']}"

    assert check_in["name"] == "Main check-in"
    assert check_in["enabled"] is True
    assert check_in["id"] > 0

    response = await admin_client.get(collection)
    assert response.status_code == 200
    assert response.json() == [check_in]

    response = await admin_client.get(individual)
    assert response.status_code == 200
    assert response.json() == check_in

    response = await admin_client.patch(
        individual,
        json={"enabled": False},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["enabled"] is False
    for field in ("id", "name", "opens_at", "closes_at", "created_at"):
        assert updated[field] == check_in[field]

    response = await admin_client.get(individual)
    assert response.status_code == 200
    assert response.json() == updated

    response = await admin_client.delete(individual)
    assert response.status_code == 204
    assert response.content == b""

    response = await admin_client.get(individual)
    assert response.status_code == 404

    response = await admin_client.get(collection)
    assert response.status_code == 200
    assert response.json() == []

    response = await admin_client.delete(individual)
    assert response.status_code == 204
    assert response.content == b""


@pytest.mark.parametrize(
    "changes",
    [
        {"closes_at": "2030-01-01T16:00:00Z"},
        {"opens_at": "2030-01-01T19:00:00Z"},
    ],
)
async def test_invalid_partial_update_preserves_saved_data(
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
    changes: dict,
):
    url = f"/api/event/{event_eid}/check-in/{check_in['id']}"

    response = await admin_client.patch(
        url,
        json={"name": "Should not be saved", **changes},
    )
    assert response.status_code == 422

    response = await admin_client.get(url)
    assert response.status_code == 200
    assert response.json() == check_in


async def test_update_can_clear_time_limits(
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
):
    url = f"/api/event/{event_eid}/check-in/{check_in['id']}"

    response = await admin_client.patch(
        url,
        json={"opens_at": None, "closes_at": None},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["opens_at"] is None
    assert updated["closes_at"] is None
    assert updated["name"] == check_in["name"]
    assert updated["enabled"] is True

    response = await admin_client.get(url)
    assert response.status_code == 200
    assert response.json() == updated


@pytest.mark.parametrize(
    ("method", "suffix", "payload", "expected_detail"),
    [
        ("GET", "", None, "Event not found."),
        (
            "GET",
            "/1",
            None,
            "Event or event check-in configuration is missing",
        ),
        ("POST", "", {"name": "Main check-in"}, "Event not found."),
        (
            "PATCH",
            "/1",
            {"enabled": False},
            "Event or event check-in configuration is missing",
        ),
        ("DELETE", "/1", None, "Event not found."),
    ],
)
async def test_missing_event_returns_not_found(
    admin_client: AsyncClient,
    method: str,
    suffix: str,
    payload: dict | None,
    expected_detail: str,
):
    url = f"/api/event/00000000000000000000000000/check-in{suffix}"

    response = await admin_client.request(method, url, json=payload)

    assert response.status_code == 404, response.text
    assert response.json() == {"detail": expected_detail}


@pytest.mark.parametrize(
    ("role", "expected_statuses"),
    [
        (None, (401, 401, 401, 401, 401)),
        (UserRole.USER, (403, 403, 403, 403, 403)),
        (UserRole.EXEC, (200, 200, 403, 403, 403)),
        (UserRole.EVENT, (403, 403, 201, 200, 204)),
        (UserRole.ADMIN, (200, 200, 201, 200, 204)),
    ],
)
@pytest.mark.parametrize(
    ("method", "suffix", "payload", "index"),
    [
        ("GET", "", None, 0),
        ("GET", "/{check_in_id}", None, 1),
        ("POST", "", {"name": "Additional check-in"}, 2),
        ("PATCH", "/{check_in_id}", {"enabled": False}, 3),
        ("DELETE", "/{check_in_id}", None, 4),
    ],
)
async def test_check_in_permissions(
    db_session: AsyncSession,
    client: AsyncClient,
    event_eid: str,
    check_in: dict,
    role: UserRole | None,
    expected_statuses: tuple[int, ...],
    method: str,
    suffix: str,
    payload: dict | None,
    index: int,
):
    client.cookies.clear()

    if role is not None:
        session_id = "check-in-permission-session"
        await create_user_session(db_session, session_id, "cintest")
        user = await get_site_user_by_computing_id(db_session, "cintest")
        assert user is not None

        db_session.add(
            SiteUserRoleDB(
                uid=user.uid,
                role=role,
                added_by=user.uid,
            )
        )
        await db_session.commit()
        client.cookies.set(
            COOKIE_SESSION_KEY,
            session_id,
            domain="test.local",
            path="/",
        )

    path = suffix.format(check_in_id=check_in["id"])
    url = f"/api/event/{event_eid}/check-in{path}"

    response = await client.request(method, url, json=payload)

    assert response.status_code == expected_statuses[index], response.text


@pytest.mark.parametrize(
    ("method", "payload", "expected_status"),
    [
        ("GET", None, 404),
        ("PATCH", {"name": "Wrong event update"}, 404),
        ("DELETE", None, 204),
    ],
)
async def test_check_in_cannot_be_accessed_through_another_event(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
    method: str,
    payload: dict | None,
    expected_status: int,
):
    start = datetime(2030, 1, 2, 17, tzinfo=UTC)
    other_event = EventDB(
        name="Unrelated event",
        description="This event does not own the check-in.",
        start_datetime=start,
        end_datetime=start + timedelta(hours=2),
        status=EventStatusEnum.SCHEDULED,
    )
    db_session.add(other_event)
    await db_session.flush()
    other_eid = other_event.eid
    await db_session.commit()

    wrong_url = f"/api/event/{other_eid}/check-in/{check_in['id']}"

    response = await admin_client.request(method, wrong_url, json=payload)

    assert response.status_code == expected_status, response.text

    original_url = f"/api/event/{event_eid}/check-in/{check_in['id']}"
    response = await admin_client.get(original_url)
    assert response.status_code == 200
    assert response.json() == check_in

    response = await admin_client.get(f"/api/event/{other_eid}/check-in")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "closes_at",
    [
        "2030-01-01T16:00:00Z",
        "2030-01-01T17:00:00Z",
    ],
)
async def test_create_rejects_invalid_time_ranges(
    admin_client: AsyncClient,
    event_eid: str,
    closes_at: str,
):
    url = f"/api/event/{event_eid}/check-in"

    response = await admin_client.post(
        url,
        json={
            "name": "Invalid check-in",
            "opens_at": "2030-01-01T17:00:00Z",
            "closes_at": closes_at,
        },
    )

    assert response.status_code == 422, response.text

    response = await admin_client.get(url)
    assert response.status_code == 200
    assert response.json() == []


async def test_update_rejects_null_name(
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
):
    url = f"/api/event/{event_eid}/check-in/{check_in['id']}"

    response = await admin_client.patch(url, json={"name": None})

    assert response.status_code == 422, response.text

    response = await admin_client.get(url)
    assert response.status_code == 200
    assert response.json() == check_in


async def test_multiple_check_ins_for_one_event_are_independent(
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
):
    collection = f"/api/event/{event_eid}/check-in"
    first_url = f"{collection}/{check_in['id']}"

    response = await admin_client.post(
        collection,
        json={"name": "Secondary check-in"},
    )
    assert response.status_code == 201, response.text
    second = response.json()
    assert second["id"] != check_in["id"]

    response = await admin_client.get(collection)
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {
        check_in["id"],
        second["id"],
    }

    response = await admin_client.patch(
        first_url,
        json={"name": "Updated main check-in"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated main check-in"

    response = await admin_client.get(f"{collection}/{second['id']}")
    assert response.status_code == 200
    assert response.json() == second

    response = await admin_client.delete(first_url)
    assert response.status_code == 204, response.text

    response = await admin_client.get(collection)
    assert response.status_code == 200
    assert response.json() == [second]

    response = await admin_client.get(first_url)
    assert response.status_code == 404


async def test_deleting_event_cascades_to_check_ins(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
):
    response = await admin_client.post(
        f"/api/event/{event_eid}/check-in",
        json={"name": "Secondary check-in"},
    )
    assert response.status_code == 201, response.text
    check_in_ids = [check_in["id"], response.json()["id"]]

    response = await admin_client.delete(f"/api/event/{event_eid}")
    assert response.status_code == 204, response.text

    # Query the child table directly so a missing parent cannot hide orphaned rows.
    query = select(EventCheckInDB.id).where(EventCheckInDB.id.in_(check_in_ids))
    remaining_ids = (await db_session.scalars(query)).all()
    assert remaining_ids == []


async def test_update_preserves_created_at_and_changes_updated_at(
    db_session: AsyncSession,
    admin_client: AsyncClient,
    event_eid: str,
    check_in: dict,
):
    url = f"/api/event/{event_eid}/check-in/{check_in['id']}"

    # Seed an older record because now() stays fixed within the test transaction.
    past = datetime(2000, 1, 1, tzinfo=UTC)
    stored = await db_session.get(EventCheckInDB, check_in["id"])
    assert stored is not None
    stored.created_at = past
    stored.updated_at = past
    await db_session.commit()

    response = await admin_client.get(url)
    assert response.status_code == 200
    before = response.json()
    assert datetime.fromisoformat(before["created_at"]) == past
    assert datetime.fromisoformat(before["updated_at"]) == past

    response = await admin_client.patch(url, json={"enabled": False})
    assert response.status_code == 200, response.text
    updated = response.json()

    assert updated["enabled"] is False
    assert updated["created_at"] == before["created_at"]
    assert datetime.fromisoformat(updated["updated_at"]) > past

    response = await admin_client.get(url)
    assert response.status_code == 200
    assert response.json() == updated
