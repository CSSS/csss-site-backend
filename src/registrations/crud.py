from collections.abc import Sequence

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from officers.constants import OfficerPositionEnum
from registrations.tables import NomineeApplication


async def get_all_registrations(
    db_session: AsyncSession
) -> Sequence[NomineeApplication]:
    registrations = (await db_session.scalars(
        sqlalchemy
        .select(NomineeApplication)
    )).all()
    return registrations

async def get_all_registrations_of_user(
    db_session: AsyncSession, computing_id: str, election_slug: str
) -> Sequence[NomineeApplication] | None:
    registrations = (
        await db_session.scalars(
            sqlalchemy.select(NomineeApplication).where(
                (NomineeApplication.computing_id == computing_id)
                & (NomineeApplication.nominee_election == election_slug)
            )
        )
    ).all()
    return registrations


async def get_one_registration_in_election(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str,
    position: OfficerPositionEnum,
) -> NomineeApplication | None:
    registration = await db_session.scalar(
        sqlalchemy.select(NomineeApplication).where(
            NomineeApplication.computing_id == computing_id,
            NomineeApplication.nominee_election == election_slug,
            NomineeApplication.position == position,
        )
    )
    return registration


async def get_all_registrations_in_election(
    db_session: AsyncSession,
    election_slug: str,
) -> Sequence[NomineeApplication] | None:
    registrations = (
        await db_session.scalars(
            sqlalchemy.select(NomineeApplication).where(NomineeApplication.nominee_election == election_slug)
        )
    ).all()
    return registrations


async def add_registration(db_session: AsyncSession, initial_application: NomineeApplication):
    db_session.add(initial_application)


async def update_registration(db_session: AsyncSession, initial_application: NomineeApplication):
    await db_session.execute(
        sqlalchemy.update(NomineeApplication)
        .where(
            (NomineeApplication.computing_id == initial_application.computing_id)
            & (NomineeApplication.nominee_election == initial_application.nominee_election)
            & (NomineeApplication.position == initial_application.position)
        )
        .values(initial_application.to_update_dict())
    )


async def delete_registration(
    db_session: AsyncSession, computing_id: str, election_slug: str, position: OfficerPositionEnum
):
    await db_session.execute(
        sqlalchemy.delete(NomineeApplication).where(
            (NomineeApplication.computing_id == computing_id)
            & (NomineeApplication.nominee_election == election_slug)
            & (NomineeApplication.position == position)
        )
    )
