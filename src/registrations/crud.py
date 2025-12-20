from collections.abc import Sequence

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from officers.constants import OfficerPositionEnum
from registrations.tables import NomineeApplicationDB


async def get_all_registrations(db_session: AsyncSession) -> Sequence[NomineeApplicationDB]:
    registrations = (await db_session.scalars(sqlalchemy.select(NomineeApplicationDB))).all()
    return registrations


async def get_all_registrations_of_user(
    db_session: AsyncSession, computing_id: str, election_slug: str
) -> Sequence[NomineeApplicationDB] | None:
    registrations = (
        await db_session.scalars(
            sqlalchemy.select(NomineeApplicationDB).where(
                (NomineeApplicationDB.computing_id == computing_id)
                & (NomineeApplicationDB.nominee_election == election_slug)
            )
        )
    ).all()
    return registrations


async def get_one_registration_in_election(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str,
    position: OfficerPositionEnum,
) -> NomineeApplicationDB | None:
    registration = await db_session.scalar(
        sqlalchemy.select(NomineeApplicationDB).where(
            NomineeApplicationDB.computing_id == computing_id,
            NomineeApplicationDB.nominee_election == election_slug,
            NomineeApplicationDB.position == position,
        )
    )
    return registration


async def get_all_registrations_in_election(
    db_session: AsyncSession,
    election_slug: str,
) -> Sequence[NomineeApplicationDB] | None:
    registrations = (
        await db_session.scalars(
            sqlalchemy.select(NomineeApplicationDB).where(NomineeApplicationDB.nominee_election == election_slug)
        )
    ).all()
    return registrations


async def add_registration(db_session: AsyncSession, initial_application: NomineeApplicationDB):
    db_session.add(initial_application)


async def update_registration(db_session: AsyncSession, initial_application: NomineeApplicationDB):
    await db_session.execute(
        sqlalchemy.update(NomineeApplicationDB)
        .where(
            (NomineeApplicationDB.computing_id == initial_application.computing_id)
            & (NomineeApplicationDB.nominee_election == initial_application.nominee_election)
            & (NomineeApplicationDB.position == initial_application.position)
        )
        .values(initial_application.to_update_dict())
    )


async def delete_registration(
    db_session: AsyncSession, computing_id: str, election_slug: str, position: OfficerPositionEnum
):
    await db_session.execute(
        sqlalchemy.delete(NomineeApplicationDB).where(
            (NomineeApplicationDB.computing_id == computing_id)
            & (NomineeApplicationDB.nominee_election == election_slug)
            & (NomineeApplicationDB.position == position)
        )
    )
