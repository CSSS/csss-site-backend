from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import delete, select

import database
from honourary.tables import HonoraryMemberDB


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


async def get_honorary_member_by_id_or_raise(
    db_session: database.DBSession,
    term_id: int,
) -> HonoraryMemberDB:
    honorary_member = await db_session.scalar(select(HonoraryMemberDB).where(HonoraryMemberDB.id == term_id))
    if honorary_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"honorary member term with id={term_id} does not exist",
        )
    return honorary_member


def ensure_term_has_not_ended(honorary_member: HonoraryMemberDB) -> None:
    if honorary_member.end_date is not None and honorary_member.end_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="cannot update or delete a term that has already ended",
        )


async def create_honorary_members(
    db_session: database.DBSession,
    honorary_members: list[HonoraryMemberDB],
) -> list[HonoraryMemberDB]:
    db_session.add_all(honorary_members)
    await db_session.flush()

    return honorary_members


async def delete_honorary_member(
    db_session: database.DBSession,
    honorary_member: HonoraryMemberDB,
) -> None:
    await db_session.execute(delete(HonoraryMemberDB).where(HonoraryMemberDB.id == honorary_member.id))
