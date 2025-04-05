import logging
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

import database
from elections.tables import Election

_logger = logging.getLogger(__name__)

@dataclass
class ElectionParameters:
    """
    Dataclass encompassing the data that can go into an Election.
    """
    slug: str
    name: str
    officer_id: str
    type: str
    start_datetime: datetime
    end_datetime: datetime
    survey_link: str

async def get_election(db_session: AsyncSession, election_slug: str) -> Election | None:
    return await db_session.scalar(
        sqlalchemy
        .select(Election)
        .where(Election.slug == election_slug)
    )

async def create_election(db_session: AsyncSession, params: ElectionParameters) -> None:
    """
    Creates a new election with given parameters.
    Does not validate if an election _already_ exists
    """
    db_session.add(Election(
        slug=params.slug,
        name=params.name,
        officer_id=params.officer_id,
        type=params.type,
        start_datetime=params.start_datetime,
        end_datetime=params.end_datetime,
        survey_link=params.survey_link
    ))

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

async def update_election(db_session: AsyncSession, params: ElectionParameters) -> None:
    """
    Updates an election with the provided parameters.
    Take care as this will replace values with None if not populated.
    You _cannot_ change the name or slug, you should instead delete and create a new election.
    Does not validate if an election _already_ exists
    """

    election = await db_session.scalar(
        sqlalchemy
        .select(Election)
        .where(slug=params.slug)
    )

    if params.start_datetime is not None:
        election.start_datetime = params.start_datetime
    if params.type is not None:
        election.type = params.type
    if params.end_datetime is not None:
        election.end_datetime = params.end_datetime
    if params.survey_link is not None:
        election.survey_link = params.survey_link

    await db_session.execute(
        sqlalchemy
        .update(Election)
        .where(Election.slug == params.slug)
        .values(election)
    )
