from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import and_, delete, extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from event.tables import EventDB
from uuid import UUID


async def get_all_events(db_session: AsyncSession) -> Sequence[EventDB]:
    events = (await db_session.scalars(select(EventDB))).all()
    return events


async def get_events_for_this_year(
    db_session: AsyncSession,
    year: int,
) -> Sequence[EventDB]:
    events = (
        await db_session.scalars(
            select(EventDB).where(
                or_(extract("year", EventDB.start_datetime) == year, extract("year", EventDB.end_datetime) == year)
            )
        )
    ).all()
    return events


async def get_events_for_this_year_month(
    db_session: AsyncSession,
    year: int,
    month: int,
) -> Sequence[EventDB]:
    events = (
        await db_session.scalars(
            select(EventDB).where(
                or_(
                    and_(extract("year", EventDB.start_datetime) == year, extract("month", EventDB.start_datetime) == month),
                    and_(extract("year", EventDB.end_datetime) == year, extract("month", EventDB.end_datetime) == month),
                )
            )
        )
    ).all()
    return events


async def get_event_by_eid(db_session: AsyncSession, eid: int) -> EventDB | None:
    return (await db_session.execute(select(EventDB).where(EventDB.eid == eid))).scalar_one_or_none()


async def get_events_by_group_id(db_session: AsyncSession, group_id: UUID) -> Sequence[EventDB] | None:
    query = select(EventDB).where(EventDB.group_id == group_id)

    result = await db_session.execute(query)

    event = result.scalars().all()

    return event


async def create_event(db_session: AsyncSession, info: EventDB):
    db_session.add(info)


async def delete_event(db_session: AsyncSession, eid: int):
    result = await db_session.execute(delete(EventDB).where(EventDB.eid == eid))
    # Return the number of rows affected
    return result.rowcount


async def delete_group_events(db_session: AsyncSession, group_id: UUID):
    result = await db_session.execute(delete(EventDB).where(EventDB.group_id == group_id))
    # Return the number of rows affected
    return result.rowcount