from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

import database
import elections
import elections.crud
import elections.tables
from elections.models import (
    ElectionParams,
    ElectionResponse,
    ElectionTypeEnum,
    ElectionUpdateParams,
    NomineeInfoModel,
    NomineeInfoUpdateParams,
)
from elections.tables import Election, NomineeInfo
from officers.constants import COUNCIL_REP_ELECTION_POSITIONS, GENERAL_ELECTION_POSITIONS, OfficerPositionEnum
from permission.types import ElectionOfficer, WebsiteAdmin
from utils.shared_models import DetailModel, SuccessResponse
from utils.urls import admin_or_raise, get_current_user, slugify

router = APIRouter(
    prefix="/elections",
    tags=["elections"],
)

async def get_user_permissions(
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

def _default_election_positions(election_type: ElectionTypeEnum) -> list[OfficerPositionEnum]:
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
    available_positions: list[OfficerPositionEnum]
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
    "",
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
    is_admin, _, _ = await get_user_permissions(request, db_session)
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
    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    is_valid_user, _, _ = await get_user_permissions(request, db_session)
    if current_time >= election.datetime_start_voting or is_valid_user:

        election_json = election.private_details(current_time)
        all_nominations = await elections.crud.get_all_registrations_in_election(db_session, slugified_name)
        if not all_nominations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="no registrations found"
            )
        election_json["candidates"] = []

        available_positions_list = election.available_positions
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
    if body.available_positions is None:
        if body.type not in ElectionTypeEnum:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid election type {body.type} for available positions"
            )
        available_positions = _default_election_positions(body.type)
    else:
        available_positions = body.available_positions

    slugified_name = slugify(body.name)
    current_time = datetime.now()
    start_nominations = datetime.fromisoformat(body.datetime_start_nominations)
    start_voting = datetime.fromisoformat(body.datetime_start_voting)
    end_voting = datetime.fromisoformat(body.datetime_end_voting)

    # TODO: We might be able to just use a validation function from Pydantic or SQLAlchemy to check this
    _raise_if_bad_election_data(
        slugified_name,
        body.type,
        start_nominations,
        start_voting,
        end_voting,
        available_positions
    )

    is_valid_user, _, _ = await get_user_permissions(request, db_session)
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
            datetime_start_nominations = start_nominations,
            datetime_start_voting = start_voting,
            datetime_end_voting = end_voting,
            available_positions = available_positions,
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
    body: ElectionUpdateParams,
    db_session: database.DBSession,
    election_name: str,
):
    is_valid_user, _, _ = await get_user_permissions(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission"
        )

    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if not election:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist",
        )

    election.update_from_params(body)

    # TODO: We might be able to just use a validation function from Pydantic or SQLAlchemy to check this
    _raise_if_bad_election_data(
        slugified_name,
        election.type,
        election.datetime_start_voting,
        election.datetime_start_voting,
        election.datetime_end_voting,
        election.available_positions,
    )

    # NOTE: If you update available positions, people will still *technically* be able to update their
    # registrations, however they will not be returned in the results.
    await elections.crud.update_election(
        db_session,
        election
    )

    await db_session.commit()

    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="couldn't find updated election")
    return JSONResponse(election.private_details(datetime.now()))

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
    slugified_name = slugify(election_name)
    is_valid_user, _, _ = await get_user_permissions(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer permission"
        )

    await elections.crud.delete_election(db_session, slugified_name)
    await db_session.commit()

    old_election = await elections.crud.get_election(db_session, slugified_name)
    return JSONResponse({"success": old_election is None})

# nominee info ------------------------------------------------------------- #

@router.get(
    "/nominee/{computing_id:str}",
    description="Nominee info is always publically tied to elections, so be careful!",
    response_model=NomineeInfoModel,
    responses={
        404: { "description": "nominee doesn't exist" }
    },
    operation_id="get_nominee"
)
async def get_nominee_info(
    request: Request,
    db_session: database.DBSession,
    computing_id: str
):
    # Putting this one behind the admin wall since it has contact information
    await admin_or_raise(request, db_session)
    nominee_info = await elections.crud.get_nominee_info(db_session, computing_id)
    if nominee_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="nominee doesn't exist"
        )

    return JSONResponse(nominee_info.serialize())

@router.patch(
    "/nominee/{computing_id:str}",
    description="Will create or update nominee info. Returns an updated copy of their nominee info.",
    response_model=NomineeInfoModel,
    responses={
        500: { "description": "Failed to retrieve updated nominee." }
    },
    operation_id="update_nominee"
)
async def provide_nominee_info(
    request: Request,
    db_session: database.DBSession,
    body: NomineeInfoUpdateParams,
    computing_id: str
):
    # TODO: There needs to be a lot more validation here.
    await admin_or_raise(request, db_session)

    updated_data = {}
    # Only update fields that were provided
    if body.full_name is not None:
        updated_data["full_name"] = body.full_name
    if body.linked_in is not None:
       updated_data["linked_in"] = body.linked_in
    if body.instagram is not None:
        updated_data["instagram"] = body.instagram
    if body.email is not None:
        updated_data["email"] = body.email
    if body.discord_username is not None:
        updated_data["discord_username"] = body.discord_username

    existing_info = await elections.crud.get_nominee_info(db_session, computing_id)
    # if not already existing, create it
    if not existing_info:
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
    if not nominee_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to get updated nominee"
        )
    return JSONResponse(nominee_info.serialize())
