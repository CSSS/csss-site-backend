import logging
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy

import database
from elections.tables import Election
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm


@dataclass
class ElectionParameters:
    """
    Dataclass encompassing the data that can go into an Election.
    """
    slug: str
    name: str
    officer_id: str
    type: str
    date: datetime
    end_date: datetime
    survey_link: str


_logger = logging.getLogger(__name__)

async def get_election(db_session: database.DBSession, election_slug: str) -> Election | None:
    query = (
        sqlalchemy
        .select(Election)
        .where(Election.slug == election_slug)
    )
    result = await db_session.scalar(query)
    return result

async def create_election(params: ElectionParameters, db_session: database.DBSession) -> None:
    """
    Creates a new election with given parameters.
    Does not validate if an election _already_ exists
    """
    election = Election(slug=params.slug,
               name=params.name,
               officer_id=params.officer_id,
               type=params.type,
               date=params.date,
               end_date=params.end_date,
               survey_link=params.survey_link)
    db_session.add(election)

async def delete_election(slug: str, db_session: database.DBSession) -> None:
    """
    Deletes a given election by its slug.
    Does not validate if an election exists
    """
    query = sqlalchemy.delete(Election).where(Election.slug == slug)
    await db_session.execute(query)

async def update_election(params: ElectionParameters, db_session: database.DBSession) -> None:
    """
    Updates an election with the provided parameters.
    Take care as this will replace values with None if not populated.
    You _cannot_ change the name or slug, you should instead delete and create a new election.
    Does not validate if an election _already_ exists
    """

    election = (await db_session.execute(sqlalchemy.select(Election).filter_by(slug=params.slug))).scalar_one()

    if params.date is not None:
        election.date = params.date
    if params.type is not None:
        election.type = params.type
    if params.end_date is not None:
        election.end_date = params.end_date
    if params.survey_link is not None:
        election.survey_link = params.survey_link

    query = sqlalchemy.update(Election).where(Election.slug == params.slug).values(election)
    await db_session.execute(query)

