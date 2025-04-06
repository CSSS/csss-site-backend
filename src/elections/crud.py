import logging

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from elections.tables import Election

_logger = logging.getLogger(__name__)

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

async def update_election(db_session: AsyncSession, new_election: Election) -> bool:
    """
    You attempting to change the name or slug will fail. Instead, you must create a new election.
    """
    target_slug = new_election.slug
    target_election = await get_election(db_session, target_slug)

    if target_election is None:
        return False
    else:
        await db_session.execute(
            sqlalchemy
            .update(Election)
            .where(Election.slug == target_slug)
            .values(new_election)
        )
        return True
