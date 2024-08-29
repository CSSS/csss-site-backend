import base64
import logging
import os
import re
import urllib.parse
from datetime import datetime
from enum import Enum

import auth
import auth.crud
import database
import elections
import requests  # TODO: make this async
import xmltodict
from constants import root_ip_address
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from permission import types

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/elections",
    tags=["elections"],
)

class ElectionType(Enum):
    GENERAL_ELECTION = "general_election"
    BY_ELECTION = "by_election"
    COUNCIL_REP_ELECTION = "council_rep_election"

def _slugify(
        text: str
) -> str:
    """
    Creates a unique slug based on text passed in. Assumes non-unicode text.
    """
    return re.sub(r"[\W_]+", "-", text)

async def _validate_user(
        db_session: database.DBSession,
        session_id: str
) -> dict:
    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    # Assuming now user is validated
    result = await types.ElectionOfficer.has_permission(db_session, computing_id)
    return result

@router.get(
    "/create_election",
    description="asdfasfasdf",
)
async def create_election(
    request: Request,
    db_session: database.DBSession,
    name: str,
    election_type: str,
    date: datetime | None = None,
    end_date: datetime | None = None,
    websurvey: str | None = None
):
    """
    aaa
    """
    session_id = request.cookies.get("session_id", None)
    user_auth = await _validate_user(db_session, session_id)
    if user_auth is False:
        # let's workshop how we actually wanna handle this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to access this resource",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Default start time should be now unless specified otherwise
    if date is None:
        date = datetime.now()

    if election_type not in [e.value for e in ElectionType]:
        raise RequestValidationError()

    params = {
        "slug" : _slugify(name),
        "name": name,
        "officer_id" : await auth.crud.get_computing_id(db_session, session_id),
        "type": election_type,
        "date": date,
        "end_date": end_date,
        "websurvey": websurvey
    }

    result = await elections.crud.create_election(params, db_session)

    #print(result)
    return {}

@router.get(
    "/test"
)
async def test():
    return {"error": "lol"}
