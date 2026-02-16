from collections.abc import Sequence

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from nominees.tables import NomineeInfoDB


async def get_all_nominees(
    db_session: AsyncSession,
) -> Sequence[NomineeInfoDB]:
    nominees = (await db_session.scalars(sqlalchemy.select(NomineeInfoDB))).all()
    return nominees


async def get_nominee_info(
    db_session: AsyncSession,
    computing_id: str,
) -> NomineeInfoDB | None:
    return await db_session.scalar(sqlalchemy.select(NomineeInfoDB).where(NomineeInfoDB.computing_id == computing_id))


async def create_nominee_info(
    db_session: AsyncSession,
    info: NomineeInfoDB,
):
    db_session.add(info)


async def update_nominee_info(
    db_session: AsyncSession,
    info: NomineeInfoDB,
):
    await db_session.execute(
        sqlalchemy.update(NomineeInfoDB)
        .where(NomineeInfoDB.computing_id == info.computing_id)
        .values(info.to_update_dict())
    )


async def delete_nominee_info(
    db_session: AsyncSession,
    computing_id: str,
):
    await db_session.execute(sqlalchemy.delete(NomineeInfoDB).where(NomineeInfoDB.computing_id == computing_id))
