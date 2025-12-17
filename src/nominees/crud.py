import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from nominees.tables import NomineeInfo


async def get_nominee_info(
    db_session: AsyncSession,
    computing_id: str,
) -> NomineeInfo | None:
    return await db_session.scalar(sqlalchemy.select(NomineeInfo).where(NomineeInfo.computing_id == computing_id))


async def create_nominee_info(
    db_session: AsyncSession,
    info: NomineeInfo,
):
    db_session.add(info)


async def update_nominee_info(
    db_session: AsyncSession,
    info: NomineeInfo,
):
    await db_session.execute(
        sqlalchemy.update(NomineeInfo)
        .where(NomineeInfo.computing_id == info.computing_id)
        .values(info.to_update_dict())
    )
