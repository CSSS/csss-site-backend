import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

import database
import elections
import elections.crud
import elections.tables
from elections.models import (
    ElectionParams,
    ElectionRegisterParams,
    ElectionResponse,
    ElectionStatusEnum,
    ElectionTypeEnum,
    NomineeApplicationModel,
    NomineeInfoModel,
)
from elections.tables import Election, NomineeApplication, NomineeInfo
from officers.constants import COUNCIL_REP_ELECTION_POSITIONS, GENERAL_ELECTION_POSITIONS, OfficerPosition
from officers.crud import get_active_officer_terms
from officers.types import OfficerPositionEnum
from permission.types import ElectionOfficer, WebsiteAdmin
from utils.shared_models import DetailModel, SuccessResponse
from utils.urls import get_current_user, logged_in_or_raise

router = APIRouter(
    prefix="/elections",
    tags=["elections"],
)

def _slugify(text: str) -> str:
    """Creates a unique slug based on text passed in. Assumes non-unicode text."""
    return re.sub(r"[\W_]+", "-", text.strip().replace("/", "").replace("&", ""))

async def _get_user_permissions(
    request: Request,
    db_session: database.DBSession,
) -> tuple[bool, str | None, str | None]:
    session_id, computing_id = await get_current_user(request, db_session)
    if not session_id or not computing_id:
        return False, None, None

    # where valid means elections officer or website admin
    has_permission = await ElectionOfficer.has_permission(db_session, computing_id)
    if not has_permission:
        has_permission = await WebsiteAdmin.has_permission(db_session, computing_id)

    return has_permission, session_id, computing_id

def _default_election_positions(election_type: ElectionTypeEnum) -> list[str]:
    if election_type == ElectionTypeEnum.GENERAL:
        available_positions = GENERAL_ELECTION_POSITIONS
    elif election_type == ElectionTypeEnum.BY_ELECTION:
        available_positions = GENERAL_ELECTION_POSITIONS
    elif election_type == ElectionTypeEnum.COUNCIL_REP:
        available_positions = COUNCIL_REP_ELECTION_POSITIONS
    return available_positions


def _raise_if_bad_election_data(
    slug: str,
    election_type: str,
    datetime_start_nominations: datetime,
    datetime_start_voting: datetime,
    datetime_end_voting: datetime,
    available_positions: list[str]
):
    if election_type not in ElectionTypeEnum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown election type {election_type}",
        )

    if datetime_start_nominations > datetime_start_voting or datetime_start_voting > datetime_end_voting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dates must be in order from earliest to latest",
        )

    for position in available_positions:
        if position not in OfficerPositionEnum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"unknown position found in position list {position}",
            )

    if len(slug) > elections.tables.MAX_ELECTION_SLUG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election slug '{slug}' is too long",
        )

# elections ------------------------------------------------------------- #

@router.get(
    "/list",
    description="Returns a list of all elections & their status",
    response_model=list[ElectionResponse],
    responses={
        404: { "description": "No elections found" }
    },
    operation_id="get_all_elections"
)
async def list_elections(
    request: Request,
    db_session: database.DBSession,
):
    is_admin, _, _ = await _get_user_permissions(request, db_session)
    election_list = await elections.crud.get_all_elections(db_session)
    if election_list is None or len(election_list) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no elections found"
        )

    current_time = datetime.now()
    if is_admin:
        election_metadata_list = [
            election.private_details(current_time)
            for election in election_list
        ]
    else:
        election_metadata_list = [
            election.public_details(current_time)
            for election in election_list
        ]

    return JSONResponse(election_metadata_list)

@router.get(
    "/{election_name:str}",
    description="""
    Retrieves the election data for an election by name.
    Returns private details when the time is allowed.
    If user is an admin or elections officer, returns computing ids for each candidate as well.
    """,
    response_model=ElectionResponse,
    responses={
        404: { "description": "Election of that name doesn't exist", "model": DetailModel }
    },
    operation_id="get_election_by_name"
)
async def get_election(
    request: Request,
    db_session: database.DBSession,
    election_name: str
):
    current_time = datetime.now()
    slugified_name = _slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_BAD_REQUEST,
            detail=f"election with slug {slugified_name} does not exist"
        )

    is_valid_user, _, _ = await _get_user_permissions(request, db_session)
    if current_time >= election.datetime_start_voting or is_valid_user:

        election_json = election.private_details(current_time)
        all_nominations = await elections.crud.get_all_registrations_in_election(db_session, slugified_name)
        if not all_nominations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="no registrations found"
            )
        election_json["candidates"] = []

        available_positions_list = election.available_positions.split(",")
        for nomination in all_nominations:
            if nomination.position not in available_positions_list:
                # ignore any positions that are **no longer** active
                continue

            # NOTE: if a nominee does not input their legal name, they are not considered a nominee
            nominee_info = await elections.crud.get_nominee_info(db_session, nomination.computing_id)
            if nominee_info is None:
                continue

            candidate_entry = {
                "position": nomination.position,
                "full_name": nominee_info.full_name,
                "linked_in": nominee_info.linked_in,
                "instagram": nominee_info.instagram,
                "email": nominee_info.email,
                "discord_username": nominee_info.discord_username,
                "speech": (
                    "No speech provided by this candidate"
                    if nomination.speech is None
                    else nomination.speech
                ),
            }
            if is_valid_user:
                candidate_entry["computing_id"] = nomination.computing_id
            election_json["candidates"].append(candidate_entry)

        # after the voting period starts, all election data becomes public
        return JSONResponse(election_json)
    else:
        election_json = election.public_details(current_time)

    return JSONResponse(election_json)

@router.post(
    "",
    description="Creates an election and places it in the database. Returns election json on success",
    response_model=ElectionResponse,
    responses={
        400: { "description": "Invalid request.", "model": DetailModel },
        500: { "model": DetailModel },
    },
    operation_id="create_election"
)
async def create_election(
    request: Request,
    body: ElectionParams,
    db_session: database.DBSession,
):
    if body.name == "list":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot use that election name",
        )

    if body.available_positions is None:
        if body.type not in ElectionTypeEnum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid election type {body.type} for available positions"
            )
        available_positions = _default_election_positions(body.type)
    else:
        available_positions = body.available_positions

    slugified_name = _slugify(body.name)
    current_time = datetime.now()

    # TODO: We might be able to just use a validation function from Pydantic or SQLAlchemy to check this
    _raise_if_bad_election_data(
        slugified_name,
        body.type,
        datetime.fromisoformat(body.datetime_start_voting),
        datetime.fromisoformat(body.datetime_start_voting),
        datetime.fromisoformat(body.datetime_end_voting),
        available_positions,
    )

    is_valid_user, _, _ = await _get_user_permissions(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission"
        )
    elif await elections.crud.get_election(db_session, slugified_name) is not None:
        # don't overwrite a previous election
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="would overwrite previous election",
        )

    await elections.crud.create_election(
        db_session,
        Election(
            slug = slugified_name,
            name = body.name,
            type = body.type,
            datetime_start_nominations = body.datetime_start_nominations,
            datetime_start_voting = body.datetime_start_voting,
            datetime_end_voting = body.datetime_end_voting,
            # TODO: Make this automatically concatenate the string and set it to lowercase if supplied with a list[str]
            available_positions = ",".join(available_positions),
            survey_link = body.survey_link
        )
    )
    await db_session.commit()

    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="couldn't fetch newly created election"
        )
    return JSONResponse(election.private_details(current_time))

@router.patch(
    "/{election_name:str}",
    description="""
        Updates an election in the database.

        Note that this doesn't let you change the name of an election, unless the new
        name produces the same slug.

        Returns election json on success.
    """,
    response_model=ElectionResponse,
    responses={
        400: { "model": DetailModel },
        401: { "description": "Bad request", "model": DetailModel },
        500: { "description": "Failed to find updated election", "model": DetailModel }
    },
    operation_id="update_election"
)
async def update_election(
    request: Request,
    body: ElectionParams,
    db_session: database.DBSession,
    election_name: str,
):
    is_valid_user, _, _ = await _get_user_permissions(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission",
            headers={"WWW-Authenticate": "Basic"},
        )

    slugified_name = _slugify(election_name)
    if await elections.crud.get_election(db_session, slugified_name) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {slugified_name} does not exist",
        )

    current_time = datetime.now()
    if body.available_positions is None:
        if body.type not in ElectionTypeEnum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid election type {body.type} for available positions"
            )
        available_positions = _default_election_positions(body.type)
    else:
        available_positions = body.available_positions

    # TODO: We might be able to just use a validation function from Pydantic or SQLAlchemy to check this
    _raise_if_bad_election_data(
        slugified_name,
        body.type,
        datetime.fromisoformat(body.datetime_start_voting),
        datetime.fromisoformat(body.datetime_start_voting),
        datetime.fromisoformat(body.datetime_end_voting),
        available_positions,
    )

    # NOTE: If you update available positions, people will still *technically* be able to update their
    # registrations, however they will not be returned in the results.
    await elections.crud.update_election(
        db_session,
        Election(
            slug = slugified_name,
            name = election_name,
            type = body.type,
            datetime_start_nominations = body.datetime_start_nominations,
            datetime_start_voting = body.datetime_start_voting,
            datetime_end_voting = body.datetime_end_voting,
            available_positions = ",".join(available_positions),
            survey_link = body.survey_link
        )
    )
    await db_session.commit()

    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="couldn't find updated election")
    return JSONResponse(election.private_details(current_time))

@router.delete(
    "/{election_name:str}",
    description="Deletes an election from the database. Returns whether the election exists after deletion.",
    response_model=SuccessResponse,
    responses={
        401: { "description": "Need to be logged in as an admin.", "model": DetailModel }
    },
    operation_id="delete_election"
)
async def delete_election(
    request: Request,
    db_session: database.DBSession,
    election_name: str
):
    slugified_name = _slugify(election_name)
    is_valid_user, _, _ = await _get_user_permissions(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer permission"
        )

    await elections.crud.delete_election(db_session, slugified_name)
    await db_session.commit()

    old_election = await elections.crud.get_election(db_session, slugified_name)
    return JSONResponse({"success": old_election is None})

# registration ------------------------------------------------------------- #

@router.get(
    "/registration/{election_name:str}",
    description="get all the registrations of a single election",
    response_model=list[NomineeApplicationModel],
    responses={
        401: { "description": "Not logged in", "model": DetailModel },
        404: { "description": "Election with slug does not exist", "model": DetailModel }
     },
    operation_id="get_election_registrations"
)
async def get_election_registrations(
    request: Request,
    db_session: database.DBSession,
    election_name: str
):
    _, computing_id = await logged_in_or_raise(request, db_session)

    slugified_name = _slugify(election_name)
    if await elections.crud.get_election(db_session, slugified_name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    registration_list = await elections.crud.get_all_registrations_of_user(db_session, computing_id, slugified_name)
    if registration_list is None:
        return JSONResponse([])
    return JSONResponse([
        item.serialize() for item in registration_list
    ])

@router.post(
    "/register",
    description="register for a specific position in this election, but doesn't set a speech",
    responses={
        400: { "description": "Bad request", "model": DetailModel },
        401: { "description": "Not logged in", "model": DetailModel },
        403: { "description": "Not an admin", "model": DetailModel },
        404: { "description": "No election found", "model": DetailModel },
    },
    operation_id="register"
)
async def register_in_election(
    request: Request,
    db_session: database.DBSession,
    body: ElectionRegisterParams,
):
    is_admin, session_id, admin_id = await _get_user_permissions(request, db_session)
    if not session_id or not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in"
        )

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="must be an admin"
        )

    if body.position not in OfficerPositionEnum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {body.position}"
        )

    if await elections.crud.get_nominee_info(db_session, body.computing_id) is None:
        # ensure that the user has a nominee info entry before allowing registration to occur.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="must have submitted nominee info before registering"
        )

    slugified_name = _slugify(body.election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    if body.position not in election.available_positions.split(","):
        # NOTE: We only restrict creating a registration for a position that doesn't exist,
        # not updating or deleting one
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.position} is not available to register for in this election"
        )

    if election.status(datetime.now()) != ElectionStatusEnum.NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registrations can only be made during the nomination period"
        )

    if await elections.crud.get_all_registrations_of_user(db_session, body.computing_id, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="person is already registered in this election"
        )

    # TODO: associate specific elections officers with specific elections, then don't
    # allow any elections officer running an election to register for it
    await elections.crud.add_registration(db_session, NomineeApplication(
        computing_id=body.computing_id,
        nominee_election=slugified_name,
        position=body.position,
        speech=None
    ))
    await db_session.commit()

@router.patch(
    "/registration/{election_name:str}/{ccid_of_registrant}",
    description="update the application of a specific registrant"
)
async def update_registration(
    request: Request,
    db_session: database.DBSession,
    election_name: str,
    ccid_of_registrant: str,
    position: str,
    speech: str | None,
):
    # check if logged in
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to update election registration"
    )
    # Leave this for now, can remove self_updates if no longer needed.
    is_self_update = (computing_id == ccid_of_registrant)
    is_officer = await get_active_officer_terms(db_session, computing_id)
    # check if the computing_id is of a valid officer or the right applicant
    if not is_officer and not is_self_update: # returns [] if user is currently not an officer
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="only valid **current** officers or the applicant can update registrations"
    )

    if position not in OfficerPosition.position_list():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {position}"
    )

    current_time = datetime.now()
    slugified_name = _slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    # self updates can only be done during nomination period. Officer updates can be done whenever
    elif election.status(current_time) != elections.tables.STATUS_NOMINATIONS and is_self_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="speeches can only be updated during the nomination period"
        )

    elif not await elections.crud.get_all_registrations_of_user(db_session, ccid_of_registrant, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="applicant not yet registered in this election"
        )

    await elections.crud.update_registration(db_session, NomineeApplication(
        computing_id=ccid_of_registrant,
        nominee_election=slugified_name,
        position=position,
        speech=speech
    ))
    await db_session.commit()

@router.delete(
    "/registration/{election_name:str}/{position:str}",
    description="revoke your registration for a specific position in this election"
)
async def delete_registration(
    request: Request,
    db_session: database.DBSession,
    election_name: str,
    position: str,
):
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to delete election registration"
        )
    elif position not in OfficerPosition.position_list():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {position}"
        )

    current_time = datetime.now()
    slugified_name = _slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )
    elif election.status(current_time) != elections.tables.STATUS_NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registration can only be revoked during the nomination period"
        )
    elif not await elections.crud.get_all_registrations_of_user(db_session, computing_id, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="you are not yet registered in this election"
        )

    await elections.crud.delete_registration(db_session, computing_id, slugified_name, position)
    await db_session.commit()

# nominee info ------------------------------------------------------------- #

@router.get(
    "/nominee/info",
    description="Nominee info is always publically tied to elections, so be careful!",
    response_model=NomineeInfoModel
)
async def get_nominee_info(
    request: Request,
    db_session: database.DBSession,
):
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to get your nominee info"
        )

    nominee_info = await elections.crud.get_nominee_info(db_session, computing_id)
    if nominee_info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You don't have any nominee info yet"
        )

    return JSONResponse(nominee_info.serialize())

@router.put(
    "/nominee/info",
    description="Will create or update nominee info. Returns an updated copy of their nominee info.",
    response_model=NomineeInfoModel
)
async def provide_nominee_info(
    request: Request,
    db_session: database.DBSession,
    full_name: str | None = None,
    linked_in: str | None = None,
    instagram: str | None = None,
    email: str | None = None,
    discord_username: str | None = None,
):
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to update nominee info"
        )

    updated_data = {}
    # Only update fields that were provided
    if full_name is not None:
        updated_data["full_name"] = full_name
    if linked_in is not None:
       updated_data["linked_in"] = linked_in
    if instagram is not None:
        updated_data["instagram"] = instagram
    if email is not None:
        updated_data["email"] = email
    if discord_username is not None:
        updated_data["discord_username"] = discord_username

    existing_info = await elections.crud.get_nominee_info(db_session, computing_id)
    # if not already existing, create it
    if not existing_info:
        # check if full name is passed
        if "full_name" not in updated_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="full name is required when creating a nominee info"
            )
        # unpack dictionary and expand into NomineeInfo class
        new_nominee_info = NomineeInfo(computing_id=computing_id, **updated_data)
        # create a new nominee
        await elections.crud.create_nominee_info(db_session, new_nominee_info)
    # else just update the partial data
    else:
        merged_data = {
            "computing_id": computing_id,
            "full_name": existing_info.full_name,
            "linked_in": existing_info.linked_in,
            "instagram": existing_info.instagram,
            "email": existing_info.email,
            "discord_username": existing_info.discord_username,
        }
        #  update the dictionary with new data
        merged_data.update(updated_data)
        updated_nominee_info = NomineeInfo(**merged_data)
        await elections.crud.update_nominee_info(db_session, updated_nominee_info)

    await db_session.commit()

    nominee_info = await elections.crud.get_nominee_info(db_session, computing_id)
    return JSONResponse(nominee_info.serialize())
