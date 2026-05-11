from collections.abc import Sequence

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from event.tables import EventDB


async def get_all_events(
    db_session: AsyncSession
) -> Sequence[EventDB]:
    events = (await db_session.scalars(sqlalchemy.select(EventDB))).all()
    return events