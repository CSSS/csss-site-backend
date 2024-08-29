import dataclasses
import logging
from datetime import datetime

import database
import sqlalchemy
from elections.models import Election
from officers.constants import OfficerPosition
from officers.models import OfficerInfo, OfficerTerm
from officers.schemas import (
    OfficerData,
    OfficerInfoData,
    OfficerPrivateData,
    OfficerTermData,
)

_logger = logging.getLogger(__name__)

async def get_election(db_session: database.DBSession, election_slug: str) -> Election | None:
    query = sqlalchemy.select(Election)
    query = query.where(Election.slug == election_slug)

    return (await db_session.execute(query)).scalar()

async def create_election(params: dict[str, datetime], db_session: database.DBSession) -> None:
    """
    Does not validate if an election _already_ exists
    """
    # TODO: actually insert stuff
    print(params)

#async def update_election(params: )
