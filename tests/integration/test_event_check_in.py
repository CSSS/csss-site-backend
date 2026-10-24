from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import create_user_session, get_site_user_by_computing_id
from auth.tables import SiteUserRoleDB
from event.constants import EventStatusEnum
from event.tables import EventDB

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
    ("method", "suffix", "payload"),
    [
        ("GET", "", None),
        ("GET", "/1", None),
        ("POST", "", {"name": "Main check-in"}),
        ("PATCH", "/1", {"enabled": False}),
        ("DELETE", "/1", None),
    ],
)
async def test_missing_event_returns_not_found(
    admin_client: AsyncClient,
    method: str,
    suffix: str,
    payload: dict | None,
):
    url = f"/api/event/00000000000000000000000000/check-in{suffix}"

    response = await admin_client.request(method, url, json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found."}


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
