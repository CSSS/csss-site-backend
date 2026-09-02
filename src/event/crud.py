from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from constants import TZ_INFO
from event.constants import EventStatusEnum
from event.tables import EventDB


async def get_all_events(db_session: AsyncSession, include_cancelled: bool) -> Sequence[EventDB]:
    """
    Get all non-cancelled events, by default.

    Args:
        db_session: database session

    Returns:
        A list of events, ordered by descending start_datetime and end_datetime.
    """
    query = select(EventDB) if include_cancelled else select(EventDB).where(EventDB.status != EventStatusEnum.CANCELLED)
    return (await db_session.scalars(query.order_by(EventDB.start_datetime.desc(), EventDB.end_datetime.desc()))).all()


async def get_events_for_this_year_month(
    db_session: AsyncSession,
    year: int,
    month: int,
    include_cancelled: bool,
) -> Sequence[EventDB]:
    """
    Gets all events that occur during the month, including ones that start before the month and year,
    and end after the month and year, assuming America/Vancouver timezone.

    Args:
        db_session: database session
        year: the year to check
        month: the month to check

    Returns:
        A list of events that overlap the month and year, ordered by ascending start_datetime and end_datetime.
    """
    period_start = datetime(year, month, 1, tzinfo=TZ_INFO)

    if month == 12:
        period_end = datetime(year + 1, 1, 1, tzinfo=TZ_INFO)
    else:
        period_end = datetime(year, month + 1, 1, tzinfo=TZ_INFO)
    query = (
        select(EventDB)
        .where(EventDB.start_datetime < period_end, EventDB.end_datetime >= period_start)
        .order_by(EventDB.start_datetime, EventDB.end_datetime)
    )

    if not include_cancelled:
        query = query.where(EventDB.status != EventStatusEnum.CANCELLED)

    events = (await db_session.scalars(query)).all()

    return events


async def get_upcoming_events(db_session: AsyncSession, include_cancelled: bool) -> Sequence[EventDB]:
    """
    Gets events that have not ended yet and are scheduled.

    Args:
        db_session: database session

    Returns:
        A list of events.
    """
    query = (
        select(EventDB)
        .where(EventDB.end_datetime > datetime.now(tz=TZ_INFO))
        .order_by(EventDB.start_datetime, EventDB.end_datetime)
    )
    if not include_cancelled:
        query = query.where(EventDB.status != EventStatusEnum.CANCELLED)

    return (await db_session.scalars(query)).all()


async def get_event_by_eid(db_session: AsyncSession, eid: int) -> EventDB | None:
    return await db_session.get(EventDB, eid)


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
