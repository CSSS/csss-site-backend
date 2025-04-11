import logging

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from elections.tables import Election, NomineeApplication

_logger = logging.getLogger(__name__)

async def get_all_elections(db_session: AsyncSession) -> list[Election] | None:
    # TODO: can this return None?
    election_list = (await db_session.scalars(
        sqlalchemy
        .select(Election)
    )).all()
    return election_list

async def get_election(db_session: AsyncSession, election_slug: str) -> Election | None:
    return await db_session.scalar(
        sqlalchemy
        .select(Election)
        .where(Election.slug == election_slug)
    )

async def create_election(db_session: AsyncSession, election: Election) -> None:
    """
    Creates a new election with given parameters.
    Does not validate if an election _already_ exists
    """
    db_session.add(election)

async def update_election(db_session: AsyncSession, new_election: Election) -> bool:
    """
    You attempting to change the name or slug will fail. Instead, you must create a new election.
    """
    target_slug = new_election.slug
    # TODO: does this check need to be performed?
    target_election = await get_election(db_session, target_slug)

    if target_election is None:
        return False
    else:
        await db_session.execute(
            sqlalchemy
            .update(Election)
            .where(Election.slug == target_slug)
            .values(new_election.to_update_dict())
        )
        return True

async def delete_election(db_session: AsyncSession, slug: str) -> None:
    """
    Deletes a given election by its slug.
    Does not validate if an election exists
    """
    await db_session.execute(
        sqlalchemy
        .delete(Election)
        .where(Election.slug == slug)
    )

# TODO: switch to only using one of application or registration
async def get_all_registrations(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str
) -> list[NomineeApplication] | None:
    registrations = (await db_session.scalars(
        sqlalchemy
        .select(NomineeApplication)
        .where(
            NomineeApplication.computing_id == computing_id
            and NomineeApplication.election_slug == election_slug
        )
    )).all()
    return registrations

async def add_registration(
    db_session: AsyncSession,
    initial_application: NomineeApplication
):
    db_session.add(initial_application)

async def update_registration(
    db_session: AsyncSession,
    initial_application: NomineeApplication
):
    await db_session.execute(
        sqlalchemy
        .update(NomineeApplication)
        .where(
            NomineeApplication.computing_id == initial_application.computing_id
            and NomineeApplication.nominee_election == initial_application.nominee_election
            and NomineeApplication.position == initial_application.position
        )
        .values(initial_application.to_update_dict())
    )

async def delete_registration(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str,
    position: str
):
    await db_session.execute(
        sqlalchemy
        .delete(NomineeApplication)
        .where(
            NomineeApplication.computing_id == computing_id
            and NomineeApplication.nominee_election == election_slug
            and NomineeApplication.position == position
        )
    )
