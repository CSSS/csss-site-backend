import logging
import re
from datetime import datetime

from crud import ElectionParameters
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from tables import election_types

import auth
import auth.crud
import database
import elections
from constants import root_ip_address
from permission.types import ElectionOfficer

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
    request: Request,
    db_session: database.DBSession,
) -> tuple[bool, str, str]:
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        return False, None, None

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if computing_id is None:
        return False, None, None

    has_permission = await ElectionOfficer.has_permission(db_session, computing_id)
    return has_permission, session_id, computing_id

@router.post(
    "/election/{name:str}",
    description="Creates an election and places it in the database",
)
async def create_election(
    request: Request,
    db_session: database.DBSession,
    name: str,
    election_type: str,
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
    survey_link: str | None = None
):
    """
    aaa
    """
    if election_type not in election_types:
        raise RequestValidationError()

    is_valid_user, session_id, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        # let's workshop how we actually wanna handle this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to access this resource",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Default start time should be now unless specified otherwise
    if start_datetime is None:
        start_datetime = datetime.now()

    params = ElectionParameters(
        _slugify(name),
        name,
        await auth.crud.get_computing_id(db_session, session_id),
        election_type,
        start_datetime,
        end_datetime,
        survey_link
    )

    await elections.crud.create_election(params, db_session)
    await db_session.commit()

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
    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        # let's workshop how we actually wanna handle this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to access this resource",
            headers={"WWW-Authenticate": "Basic"},
        )

    if slug is not None:
        await elections.crud.delete_election(slug, db_session)
        await db_session.commit()

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
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
    survey_link: str | None = None
):
    is_valid_user, session_id, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        # let's workshop how we actually wanna handle this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have permission to access this resource",
            headers={"WWW-Authenticate": "Basic"},
        )
    elif slug is not None:
        params = ElectionParameters(
            _slugify(name),
            name,
            await auth.crud.get_computing_id(db_session, session_id),
            election_type,
            start_datetime,
            end_datetime,
            survey_link
        )
        await elections.crud.update_election(params, db_session)
        await db_session.commit()

@router.get(
    "/test"
)
async def test():
    return {"error": "lol"}
