from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient

from config import settings
from database import DBSession
from event.constants import EventStatusEnum
from event.tables import EventDB
from image_asset.tables import ImageAssetDB

pytestmark = pytest.mark.asyncio(loop_scope="session")


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
