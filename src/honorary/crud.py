from datetime import date

from sqlalchemy import delete, select

import database
from honorary.tables import HonoraryMemberDB


async def get_all_honorary_members(db_session: database.DBSession) -> list[HonoraryMemberDB]:
    query = select(HonoraryMemberDB).order_by(HonoraryMemberDB.start_date.desc())
    return list((await db_session.scalars(query)).all())


async def get_current_honorary_members(db_session: database.DBSession) -> list[HonoraryMemberDB]:
    today = date.today()
    query = (
        select(HonoraryMemberDB)
        .where(
            (HonoraryMemberDB.start_date <= today)
            & ((HonoraryMemberDB.end_date >= today) | HonoraryMemberDB.end_date.is_(None))
        )
        .order_by(HonoraryMemberDB.start_date.desc())
    )
    return list((await db_session.scalars(query)).all())


async def get_honorary_member_by_id(
    db_session: database.DBSession,
    term_id: int,
) -> HonoraryMemberDB | None:
    return await db_session.scalar(select(HonoraryMemberDB).where(HonoraryMemberDB.id == term_id))


def has_term_ended(honorary_member: HonoraryMemberDB) -> bool:
    return honorary_member.end_date is not None and honorary_member.end_date < date.today()


async def create_honorary_members(
    db_session: database.DBSession,
    honorary_members: list[HonoraryMemberDB],
) -> list[HonoraryMemberDB]:
    db_session.add_all(honorary_members)
    return honorary_members


async def delete_honorary_member(
    db_session: database.DBSession,
    honorary_member: HonoraryMemberDB,
) -> None:
    await db_session.execute(delete(HonoraryMemberDB).where(HonoraryMemberDB.id == honorary_member.id))
