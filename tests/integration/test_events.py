from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient

from config import settings
from database import DBSession
from event.constants import EventStatusEnum
from event.models import EventCreate
from event.tables import EventDB
from image_asset.tables import ImageAssetDB

pytestmark = pytest.mark.asyncio(loop_scope="session")

UPDATE_EVENT_START = datetime(2030, 1, 1, 18, tzinfo=UTC)
UPDATE_EVENT_END = UPDATE_EVENT_START + timedelta(hours=2)
ORIGINAL_IMAGE_KEY = "images/update-event-original.png"
REPLACEMENT_IMAGE_KEY = "images/update-event-replacement.png"


async def seed_events(db_session: DBSession) -> None:
    now = datetime.now(UTC)
    image = ImageAssetDB(
        storage_key="images/ongoing-event.png",
        original_filename="ongoing-event.png",
    )
    db_session.add(image)
    await db_session.flush()

    db_session.add_all(
        [
            EventDB(
                name="Past event",
                description="A scheduled event that has ended.",
                start_datetime=now - timedelta(days=4),
                end_datetime=now - timedelta(days=3),
                status=EventStatusEnum.SCHEDULED,
            ),
            EventDB(
                name="Ongoing event",
                description="A scheduled event that has started but not ended.",
                start_datetime=now - timedelta(days=1),
                end_datetime=now + timedelta(days=1),
                status=EventStatusEnum.SCHEDULED,
                image_id=image.image_id,
            ),
            EventDB(
                name="Future event",
                description="A scheduled event that has not started.",
                start_datetime=now + timedelta(days=2),
                end_datetime=now + timedelta(days=3),
                status=EventStatusEnum.SCHEDULED,
            ),
            EventDB(
                name="Cancelled future event",
                description="A cancelled event that has not started.",
                start_datetime=now + timedelta(days=4),
                end_datetime=now + timedelta(days=5),
                status=EventStatusEnum.CANCELLED,
            ),
        ]
    )
    await db_session.commit()


async def seed_event_for_update(db_session: DBSession) -> tuple[int, int, int]:
    original_image = ImageAssetDB(
        storage_key=ORIGINAL_IMAGE_KEY,
        original_filename="update-event-original.png",
    )
    replacement_image = ImageAssetDB(
        storage_key=REPLACEMENT_IMAGE_KEY,
        original_filename="update-event-replacement.png",
    )
    db_session.add_all([original_image, replacement_image])
    await db_session.flush()

    event = EventDB(
        name="Event to update",
        description="Original description.",
        start_datetime=UPDATE_EVENT_START,
        end_datetime=UPDATE_EVENT_END,
        status=EventStatusEnum.SCHEDULED,
        image_id=original_image.image_id,
    )
    db_session.add(event)
    await db_session.flush()

    ids = event.eid, original_image.image_id, replacement_image.image_id
    await db_session.commit()
    return ids


@pytest.mark.parametrize(
    ("params", "expected_names"),
    [
        ({}, ["Past event", "Ongoing event", "Future event"]),
        (
            {"include_cancelled": "true"},
            ["Past event", "Ongoing event", "Future event", "Cancelled future event"],
        ),
        ({"current": "true"}, ["Ongoing event", "Future event"]),
        (
            {"current": "true", "include_cancelled": "true"},
            ["Ongoing event", "Future event", "Cancelled future event"],
        ),
    ],
    ids=["defaults", "include-cancelled", "current", "current-and-include-cancelled"],
)
async def test__get_events_applies_filters(
    db_session: DBSession,
    client: AsyncClient,
    params: dict[str, str],
    expected_names: list[str],
):
    await seed_events(db_session)

    response = await client.get("/api/event", params=params)

    assert response.status_code == status.HTTP_200_OK
    assert [event["name"] for event in response.json()] == expected_names


async def test__get_events_sorts_descending(db_session: DBSession, client: AsyncClient):
    await seed_events(db_session)

    response = await client.get("/api/event", params={"desc": "true"})

    assert response.status_code == status.HTTP_200_OK
    assert [event["name"] for event in response.json()] == [
        "Future event",
        "Ongoing event",
        "Past event",
    ]


async def test__get_events_includes_image_url_without_dropping_unlinked_events(
    db_session: DBSession,
    client: AsyncClient,
):
    await seed_events(db_session)

    response = await client.get("/api/event")

    assert response.status_code == status.HTTP_200_OK
    events_by_name = {event["name"]: event for event in response.json()}
    assert events_by_name["Ongoing event"]["image_url"] == (
        f"{settings.media_base_url.rstrip('/')}/images/ongoing-event.png"
    )
    assert events_by_name["Past event"]["image_url"] is None


async def test__get_events_rejects_invalid_boolean_query_params(client: AsyncClient):
    response = await client.get("/api/event", params={"current": "not-a-boolean"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test__update_event_preserves_image_when_image_id_is_omitted(
    db_session: DBSession,
    admin_client: AsyncClient,
):
    event_id, original_image_id, _ = await seed_event_for_update(db_session)

    response = await admin_client.patch(
        f"/api/event/{event_id}",
        json={"name": "Updated event"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Updated event"
    assert response.json()["image_id"] == original_image_id
    assert response.json()["image_url"] == f"{settings.media_base_url.rstrip('/')}/{ORIGINAL_IMAGE_KEY}"

    db_event = await db_session.get(EventDB, event_id, populate_existing=True)
    assert db_event is not None
    assert db_event.name == "Updated event"
    assert db_event.image_id == original_image_id


async def test__update_event_preserves_image_when_image_id_is_unchanged(
    db_session: DBSession,
    admin_client: AsyncClient,
):
    event_id, original_image_id, _ = await seed_event_for_update(db_session)

    response = await admin_client.patch(
        f"/api/event/{event_id}",
        json={"image_id": original_image_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["image_id"] == original_image_id
    assert response.json()["image_url"] == f"{settings.media_base_url.rstrip('/')}/{ORIGINAL_IMAGE_KEY}"

    db_event = await db_session.get(EventDB, event_id, populate_existing=True)
    assert db_event is not None
    assert db_event.image_id == original_image_id


async def test__update_event_replaces_image(
    db_session: DBSession,
    admin_client: AsyncClient,
):
    event_id, _, replacement_image_id = await seed_event_for_update(db_session)

    response = await admin_client.patch(
        f"/api/event/{event_id}",
        json={"image_id": replacement_image_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["image_id"] == replacement_image_id
    assert response.json()["image_url"] == f"{settings.media_base_url.rstrip('/')}/{REPLACEMENT_IMAGE_KEY}"

    db_event = await db_session.get(EventDB, event_id, populate_existing=True)
    assert db_event is not None
    assert db_event.image_id == replacement_image_id


async def test__update_event_clears_image_when_image_id_is_null(
    db_session: DBSession,
    admin_client: AsyncClient,
):
    event_id, _, _ = await seed_event_for_update(db_session)

    response = await admin_client.patch(
        f"/api/event/{event_id}",
        json={"image_id": None},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["image_id"] is None
    assert response.json()["image_url"] is None

    db_event = await db_session.get(EventDB, event_id, populate_existing=True)
    assert db_event is not None
    assert db_event.image_id is None


async def test__update_event_rejects_missing_image_without_modifying_event(
    db_session: DBSession,
    admin_client: AsyncClient,
):
    event_id, original_image_id, _ = await seed_event_for_update(db_session)

    response = await admin_client.patch(
        f"/api/event/{event_id}",
        json={"image_id": 0},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Image asset doesn't exist."}

    db_event = await db_session.get(EventDB, event_id, populate_existing=True)
    assert db_event is not None
    assert db_event.image_id == original_image_id


async def test__update_event_validates_the_merged_time_range(
    db_session: DBSession,
    admin_client: AsyncClient,
):
    event_id, _, _ = await seed_event_for_update(db_session)

    response = await admin_client.patch(
        f"/api/event/{event_id}",
        json={"start_datetime": (UPDATE_EVENT_END + timedelta(hours=1)).isoformat()},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    db_event = await db_session.get(EventDB, event_id, populate_existing=True)
    assert db_event is not None
    assert db_event.start_datetime == UPDATE_EVENT_START


async def test__update_event_returns_not_found_for_missing_event(admin_client: AsyncClient):
    response = await admin_client.patch("/api/event/0", json={"name": "Missing event"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Event doesn't exist."}


async def test__update_event_requires_authentication(client: AsyncClient):
    response = await client.patch("/api/event/0", json={"name": "Unauthorized update"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__create_event_returns_url(db_session: DBSession, admin_client: AsyncClient):
    image = ImageAssetDB(
        storage_key="images/new-event.png",
        original_filename="new-event.png",
    )
    db_session.add(image)
    await db_session.flush()
    now = datetime.now(UTC).isoformat()

    response = await admin_client.post(
        "/api/event",
        json={
            "name": "New Event",
            "description": "Description",
            "start_datetime": now,
            "end_datetime": now,
            "status": EventStatusEnum.SCHEDULED,
            "image_id": image.image_id,
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["image_url"] == f"{settings.media_base_url}/images/new-event.png"
