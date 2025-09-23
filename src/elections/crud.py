from collections.abc import Sequence

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from elections.tables import Election


async def get_all_elections(db_session: AsyncSession) -> Sequence[Election]:
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
