from collections.abc import Sequence

from sqlalchemy import select, or_, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from event.tables import EventDB

from datetime import datetime, date


async def get_all_events(
    db_session: AsyncSession
) -> Sequence[EventDB]:
    events = (await db_session.scalars(select(EventDB))).all()
    return events


async def get_events_for_this_year(
    db_session: AsyncSession,
    year: int,
) -> Sequence[EventDB]:
    events = (await db_session.scalars(select(EventDB).where
    (
        or_(
            extract('year', EventDB.start_time) == year, 
            extract('year', EventDB.end_time) == year
        )
    ))).all()
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
                    and_(
                        extract('year', EventDB.start_time) == year,
                        extract('month', EventDB.start_time) == month
                    ),
                    and_(
                        extract('year', EventDB.end_time) == year,
                        extract('month', EventDB.end_time) == month
                    )
                )
            )
        )
    ).all()
    return events