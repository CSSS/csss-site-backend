from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, delete, extract, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from event.tables import EventDB


async def get_all_events(db_session: AsyncSession) -> Sequence[EventDB] | None:
    return (await db_session.scalars(select(EventDB))).all()
    


async def get_events_for_this_year(
    db_session: AsyncSession,
    year: int,
) -> Sequence[EventDB] | None:
    query = select(EventDB).where(
        or_(
            extract("year", EventDB.start_datetime) == year,
            extract("year", EventDB.end_datetime) == year
        )
    )

    result = await db_session.scalars(query)

    events = result.all()

    return events


async def get_events_for_this_year_month(
    db_session: AsyncSession,
    year: int,
    month: int,
) -> Sequence[EventDB] | None:
    query = select(EventDB).where(
                or_(
                    and_(extract("year", EventDB.start_datetime) == year, extract("month", EventDB.start_datetime) == month),
                    and_(extract("year", EventDB.end_datetime) == year, extract("month", EventDB.end_datetime) == month),
                )
            )

    events = (
        await db_session.scalars(
            query
        )
    ).all()

    return events


async def get_event_by_eid(
    db_session: AsyncSession,
    eid: int
) -> EventDB | None:
    return await db_session.get(EventDB, eid)


async def get_events_by_group_id(
    db_session: AsyncSession,
    group_id: UUID
) -> Sequence[EventDB] | None:
    query = select(EventDB).where(EventDB.group_id == group_id)

    result = await db_session.execute(query)

    return result.scalars().all()


async def create_event(db_session: AsyncSession, info: EventDB):
    db_session.add(info)

async def create_bulk_event(db_session: AsyncSession, events: list[EventDB]):
    db_session.add_all(events)

async def delete_event(
    db_session: AsyncSession,
    eid: int
) -> int | None:
    query = (
        delete(EventDB)
        .where(EventDB.eid == eid)
        .returning(EventDB.eid)
    )
    return await db_session.scalar(query)


async def delete_group_events(
    db_session: AsyncSession,
    group_id: UUID
) -> Sequence[int] | None:
    query = (
        delete(EventDB)
        .where(EventDB.group_id == group_id)
        .returning(EventDB.eid)
    )

    return (await db_session.scalars(query)).all()
