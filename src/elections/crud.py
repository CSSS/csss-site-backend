import dataclasses
import logging
from datetime import datetime

import database
import sqlalchemy
from elections.tables import Election
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import (
    OfficerData,
    OfficerInfoData,
    OfficerPrivateData,
    OfficerTermData,
)

_logger = logging.getLogger(__name__)

async def get_election(db_session: database.DBSession, election_slug: str) -> Election | None:
    query = sqlalchemy.select(Election)
    query = query.where(Election.slug == election_slug)
    result = (await db_session.execute(query)).scalar()
    db_session.commit()
    return result

async def create_election(params: dict[str, datetime], db_session: database.DBSession) -> None:
    """
    Creates a new election with given parameters.
    Does not validate if an election _already_ exists
    """
    election = Election(slug=params["slug"],
               name=params["name"],
               officer_id=params["officer_id"],
               type=params["type"],
               date=params["date"],
               end_date=params["end_date"],
               websurvey=params["websurvey"])
    db_session.add(election)
    await db_session.commit()

async def delete_election(slug: str, db_session: database.DBSession) -> None:
    """
    Deletes a given election by its slug.
    Does not validate if an election exists
    """
    query = sqlalchemy.delete(Election).where(Election.slug == slug)
    await db_session.execute(query)
    await db_session.commit()

async def update_election(params: dict[str, datetime], db_session: database.DBSession) -> None:
    """
    Updates an election with the provided parameters.
    Take care as this will replace values with None if not populated.
    You _cannot_ change the name or slug, you should instead delete and create a new election.
    Does not validate if an election _already_ exists
    """

    election = (await db_session.execute(sqlalchemy.select(Election).filter_by(slug=params["slug"]))).scalar_one()

    if params["date"] is not None:
        election.date = params["date"]
    if params["type"] is not None:
        election.type = params["type"]
    if params["end_date"] is not None:
        election.end_date = params["end_date"]
    if params["websurvey"] is not None:
        election.websurvey = params["websurvey"]

    await db_session.commit()


    # query = sqlalchemy.update(Election).where(Election.slug == params["slug"]).values(election)
    # await db_session.execute(query)

