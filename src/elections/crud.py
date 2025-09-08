import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from elections.tables import Election, NomineeApplication, NomineeInfo
from officers.types import OfficerPositionEnum


async def get_all_elections(db_session: AsyncSession) -> list[Election]:
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

async def create_election(db_session: AsyncSession, election: Election):
    """
    Creates a new election with given parameters.
    Does not validate if an election _already_ exists
    """
    db_session.add(election)

async def update_election(db_session: AsyncSession, new_election: Election):
    """
    Attempting to change slug will fail. Instead, you must create a new election.
    """
    await db_session.execute(
        sqlalchemy
        .update(Election)
        .where(Election.slug == new_election.slug)
        .values(new_election.to_update_dict())
    )

async def delete_election(db_session: AsyncSession, slug: str) -> None:
    """
    Deletes a given election by its slug. Does not validate if an election exists
    """
    await db_session.execute(
        sqlalchemy
        .delete(Election)
        .where(Election.slug == slug)
    )

# ------------------------------------------------------- #

# TODO: switch to only using one of application or registration
async def get_all_registrations_of_user(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str
) -> list[NomineeApplication] | None:
    registrations = (await db_session.scalars(
        sqlalchemy
        .select(NomineeApplication)
        .where(
            (NomineeApplication.computing_id == computing_id)
            & (NomineeApplication.nominee_election == election_slug)
        )
    )).all()
    return registrations

async def get_one_registration_in_election(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str,
    position: OfficerPositionEnum,
) -> NomineeApplication | None:
    registration = (await db_session.scalar(
        sqlalchemy
        .select(NomineeApplication)
        .where(
            NomineeApplication.computing_id == computing_id,
            NomineeApplication.nominee_election == election_slug,
            NomineeApplication.position == position
        )
    ))
    return registration

async def get_all_registrations_in_election(
    db_session: AsyncSession,
    election_slug: str,
) -> list[NomineeApplication] | None:
    registrations = (await db_session.scalars(
        sqlalchemy
        .select(NomineeApplication)
        .where(
            NomineeApplication.nominee_election == election_slug
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
            (NomineeApplication.computing_id == initial_application.computing_id)
            & (NomineeApplication.nominee_election == initial_application.nominee_election)
            & (NomineeApplication.position == initial_application.position)
        )
        .values(initial_application.to_update_dict())
    )

async def delete_registration(
    db_session: AsyncSession,
    computing_id: str,
    election_slug: str,
    position: OfficerPositionEnum
):
    await db_session.execute(
        sqlalchemy
        .delete(NomineeApplication)
        .where(
            (NomineeApplication.computing_id == computing_id)
            & (NomineeApplication.nominee_election == election_slug)
            & (NomineeApplication.position == position)
        )
    )

# ------------------------------------------------------- #

async def get_nominee_info(
    db_session: AsyncSession,
    computing_id: str,
) -> NomineeInfo | None:
    return await db_session.scalar(
        sqlalchemy
        .select(NomineeInfo)
        .where(NomineeInfo.computing_id == computing_id)
    )

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
        sqlalchemy
        .update(NomineeInfo)
        .where(NomineeInfo.computing_id == info.computing_id)
        .values(info.to_update_dict())
    )
