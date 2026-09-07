from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from constants import TZ_INFO
from event.constants import EventStatusEnum
from event.models import Event, GetEventQueryParams
from event.tables import EventDB
from image_asset.tables import ImageAssetDB

MEDIA_BASE_URL = settings.media_base_url.rstrip("/")


def make_image_url(storage_key: str | None) -> str | None:
    return f"{MEDIA_BASE_URL}/{storage_key}" if storage_key is not None else None


async def get_events(db_session: AsyncSession, q: GetEventQueryParams) -> list[Event]:
    query = select(EventDB, ImageAssetDB.storage_key).outerjoin(ImageAssetDB, EventDB.image_id == ImageAssetDB.image_id)

    if q.current:
        query = query.where(EventDB.end_datetime > datetime.now(tz=TZ_INFO))

    if not q.include_cancelled:
        query = query.where(EventDB.status != EventStatusEnum.CANCELLED)

    query = (
        query.order_by(EventDB.start_datetime.desc(), EventDB.end_datetime.desc())
        if q.desc
        else query.order_by(EventDB.start_datetime.asc(), EventDB.end_datetime.asc())
    )

    rows = (await db_session.execute(query)).all()

    return [
        Event.model_validate(event).model_copy(update={"image_url": make_image_url(storage_key)})
        for event, storage_key in rows
    ]


async def get_event_by_eid(db_session: AsyncSession, eid: int) -> EventDB | None:
    return await db_session.get(EventDB, eid)


async def get_event_with_image_url(db_session: AsyncSession, eid: int) -> tuple[EventDB, str | None] | None:
    query = (
        select(EventDB, ImageAssetDB.storage_key)
        .outerjoin(ImageAssetDB, EventDB.image_id == ImageAssetDB.image_id)
        .where(EventDB.eid == eid)
    )
    row = (await db_session.execute(query)).one_or_none()
    if row is None:
        return None
    db_event, storage_key = row
    return db_event, make_image_url(storage_key)


async def get_events_by_group_id(db_session: AsyncSession, group_id: UUID) -> Sequence[EventDB]:
    query = select(EventDB).where(EventDB.group_id == group_id).order_by(EventDB.start_datetime, EventDB.end_datetime)

    result = await db_session.execute(query)

    return result.scalars().all()


def create_event(db_session: AsyncSession, info: EventDB) -> None:
    db_session.add(info)


def create_bulk_event(db_session: AsyncSession, events: list[EventDB]) -> None:
    db_session.add_all(events)


async def delete_event(db_session: AsyncSession, eid: int) -> int | None:
    query = delete(EventDB).where(EventDB.eid == eid).returning(EventDB.eid)
    return await db_session.scalar(query)


async def delete_group_events(db_session: AsyncSession, group_id: UUID) -> Sequence[int]:
    query = delete(EventDB).where(EventDB.group_id == group_id).returning(EventDB.eid)

    return (await db_session.scalars(query)).all()
