import base64
import logging
import os
import re
import urllib.parse
from datetime import datetime

import requests  # TODO: make this async
import xmltodict
from fastapi import APIRouter, BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError

import auth
import auth.crud
import database
import elections
from constants import root_ip_address
from permission import types

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/elections",
    tags=["elections"],
)

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
    description="Creates an election and places it in the database",
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

    await elections.crud.create_election(params, db_session)

    # TODO: create a suitable json response
    return {}

@router.get(
        "/delete_election",
        description="Deletes an election from the database"
)
async def delete_election(
    request: Request,
    db_session: database.DBSession,
    slug: str
):
    session_id = request.cookies.get("session_id", None)
    user_auth = await _validate_user(db_session, session_id)
    if user_auth is False:
        # let's workshop how we actually wanna handle this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to access this resource",
            headers={"WWW-Authenticate": "Basic"},
        )

    if slug is not None:
        await elections.crud.delete_election(slug, db_session)

@router.get(
    "/update_election",
    description="""Updates an election in the database.
                   Note that this does not allow you to change the _name_ of an election as this would generate a new slug."""
)
async def update_election(
    request: Request,
    db_session: database.DBSession,
    slug: str,
    name: str,
    election_type: str,
    date: datetime | None = None,
    end_date: datetime | None = None,
    websurvey: str | None = None
):
    session_id = request.cookies.get("session_id", None)
    user_auth = await _validate_user(db_session, session_id)
    if user_auth is False:
        # let's workshop how we actually wanna handle this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to access this resource",
            headers={"WWW-Authenticate": "Basic"},
        )
    if slug is not None:
        params = {
            "slug" : slug,
            "name" : name,
            "officer_id" : await auth.crud.get_computing_id(db_session, session_id),
            "type": election_type,
            "date": date,
            "end_date": end_date,
            "websurvey": websurvey
        }
        await elections.crud.update_election(params, db_session)


@router.get(
    "/test"
)
async def test():
    return {"error": "lol"}
