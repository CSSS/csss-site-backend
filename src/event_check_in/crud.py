from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from event_check_in.models import EventCheckInCreate
from event_check_in.tables import EventCheckInDB


async def get_check_ins(
    db_session: AsyncSession,
    event_id: int,
) -> list[EventCheckInDB]:
    query = select(EventCheckInDB).where(EventCheckInDB.event_id == event_id).order_by(EventCheckInDB.id)
    return list((await db_session.scalars(query)).all())


async def get_check_in(
    db_session: AsyncSession,
    event_id: int,
    check_in_id: int,
    *,
    for_update: bool = False,
) -> EventCheckInDB | None:
    query = select(EventCheckInDB).where(
        EventCheckInDB.event_id == event_id,
        EventCheckInDB.id == check_in_id,
    )

    if for_update:
        query = query.with_for_update()

    return await db_session.scalar(query)


def create_check_in(
    db_session: AsyncSession,
    event_id: int,
    data: EventCheckInCreate,
) -> EventCheckInDB:
    check_in = EventCheckInDB(event_id=event_id, **data.model_dump())
    db_session.add(check_in)
    return check_in


def update_check_in(
    check_in: EventCheckInDB,
    data: EventCheckInCreate,
) -> None:
    for field, value in data.model_dump().items():
        setattr(check_in, field, value)


async def delete_check_in(
    db_session: AsyncSession,
    event_id: int,
    check_in_id: int,
) -> int | None:
    query = (
        delete(EventCheckInDB)
        .where(
            EventCheckInDB.event_id == event_id,
            EventCheckInDB.id == check_in_id,
        )
        .returning(EventCheckInDB.id)
    )
    return await db_session.scalar(query)
