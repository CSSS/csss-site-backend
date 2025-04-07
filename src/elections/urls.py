import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import database
import elections
from elections.tables import Election, election_types
from permission.types import ElectionOfficer, WebsiteAdmin
from utils.urls import is_logged_in

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/elections",
    tags=["elections"],
)

def _slugify(text: str) -> str:
    """Creates a unique slug based on text passed in. Assumes non-unicode text."""
    return re.sub(r"[\W_]+", "-", text.strip().replace("/", "").replace("&", ""))

async def _validate_user(
    request: Request,
    db_session: database.DBSession,
) -> tuple[bool, str, str]:
    logged_in, session_id, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        return False, None, None

    has_permission = await ElectionOfficer.has_permission(db_session, computing_id)
    if not has_permission:
        has_permission = await WebsiteAdmin.has_permission(db_session, computing_id)

    return has_permission, session_id, computing_id

# elections ------------------------------------------------------------- #

@router.get(
    "/by_name/{name:str}",
    description="Retrieves the election data for an election by name"
)
async def get_election(
    request: Request,
    db_session: database.DBSession,
    name: str,
):
    election = await elections.crud.get_election(db_session, _slugify(name))
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {_slugify(name)} does not exist"
        )
    elif datetime.now() >= election.datetime_start_voting:
        # after the voting period starts, all election data becomes public
        return JSONResponse(election.serializable_dict())

    is_valid_user, _, _ = await _validate_user(request, db_session)
    return JSONResponse(
        election.serializable_dict()
        if is_valid_user
        else election.public_details()
    )

@router.post(
    "/by_name/{name:str}",
    description="Creates an election and places it in the database. Returns election json on success",
)
async def create_election(
    request: Request,
    db_session: database.DBSession,
    name: str,
    election_type: str,
    datetime_start_nominations: datetime,
    datetime_start_voting: datetime,
    datetime_end_voting: datetime,
    survey_link: str | None,
):
    if election_type not in election_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown election type {election_type}",
        )

    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission",
            # TODO: is this header actually required?
            headers={"WWW-Authenticate": "Basic"},
        )
    elif len(name) > elections.tables.MAX_ELECTION_NAME:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election name {name} is too long",
        )
    elif len(_slugify(name)) > elections.tables.MAX_ELECTION_SLUG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election slug {_slugify(name)} is too long",
        )
    elif await elections.crud.get_election(db_session, _slugify(name)) is not None:
        # don't overwrite a previous election
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="would overwrite previous election",
        )
    elif not (
        (datetime_start_nominations <= datetime_start_voting)
        and (datetime_start_voting <= datetime_end_voting)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dates must be in order from earliest to latest",
        )

    await elections.crud.create_election(
        db_session,
        Election(
            slug = _slugify(name),
            name = name,
            type = election_type,
            datetime_start_nominations = datetime_start_nominations,
            datetime_start_voting = datetime_start_voting,
            datetime_end_voting = datetime_end_voting,
            survey_link = survey_link
        )
    )
    await db_session.commit()

    election = await elections.crud.get_election(db_session, _slugify(name))
    return JSONResponse(election.serializable_dict())

@router.patch(
    "/by_name/{name:str}",
    description="""
        Updates an election in the database.

        Note that this doesn't let you change the name of an election, unless the new
        name produces the same slug.

        Returns election json on success.
    """
)
async def update_election(
    request: Request,
    db_session: database.DBSession,
    name: str,
    election_type: str,
    datetime_start_nominations: datetime,
    datetime_start_voting: datetime,
    datetime_end_voting: datetime,
    survey_link: str | None,
):
    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        # let's workshop how we actually wanna handle this
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission",
            headers={"WWW-Authenticate": "Basic"},
        )
    elif not (
        (datetime_start_nominations <= datetime_start_voting)
        and (datetime_start_voting <= datetime_end_voting)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dates must be in order from earliest to latest",
        )

    new_election = Election(
        slug = _slugify(name),
        name = name,
        type = election_type,
        datetime_start_nominations = datetime_start_nominations,
        datetime_start_voting = datetime_start_voting,
        datetime_end_voting = datetime_end_voting,
        survey_link = survey_link
    )
    success = await elections.crud.update_election(db_session, new_election)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {_slugify(name)} does not exist",
        )
    else:
        await db_session.commit()

        election = await elections.crud.get_election(db_session, _slugify(name))
        return JSONResponse(election.serializable_dict())

@router.delete(
    "/by_name/{name:str}",
    description="Deletes an election from the database. Returns whether the election exists after deletion."
)
async def delete_election(
    request: Request,
    db_session: database.DBSession,
    name: str
):
    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer permission",
            # TODO: is this header actually required?
            headers={"WWW-Authenticate": "Basic"},
        )

    await elections.crud.delete_election(db_session, _slugify(name))
    await db_session.commit()

    old_election = await elections.crud.get_election(db_session, _slugify(name))
    return JSONResponse({"exists": old_election is not None})

# registration ------------------------------------------------------------- #

@router.post(
    "/register/{name:str}",
    description="allows a user to register for an election"
)
async def register_in_election(
    request: Request,
    db_session: database.DBSession,
    name: str
):
    # TODO: associate specific elections officers with specific elections, then don't
    # allow any elections officer running an election to register for it
    pass

@router.patch(
    "/register/{name:str}",
    description="update your registration for an election"
)
async def update_registration(
    request: Request,
    db_session: database.DBSession,
    name: str
):
    pass

@router.delete(
    "/register/{name:str}",
    description="revoke your registration in the election"
)
async def delete_registration(
    request: Request,
    db_session: database.DBSession,
    name: str
):
    pass
