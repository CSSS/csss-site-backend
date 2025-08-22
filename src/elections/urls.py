import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

import database
import elections
import elections.tables
from elections.tables import Election, NomineeApplication, NomineeInfo, election_types
from officers.constants import OfficerPosition
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

    # where valid means elections officer or website admin
    has_permission = await ElectionOfficer.has_permission(db_session, computing_id)
    if not has_permission:
        has_permission = await WebsiteAdmin.has_permission(db_session, computing_id)

    return has_permission, session_id, computing_id

# elections ------------------------------------------------------------- #

@router.get(
    "/list",
    description="Returns a list of all elections & their status"
)
async def list_elections(
    _: Request,
    db_session: database.DBSession,
):
    election_list = await elections.crud.get_all_elections(db_session)
    if election_list is None or len(election_list) == 0:
        raise HTTPException(
            status_code=status.HTTP_404_INTERNAL_SERVER_ERROR,
            detail="no elections found"
        )

    current_time = datetime.now()
    election_metadata_list = [
        election.public_metadata(current_time)
        for election in election_list
    ]

    return JSONResponse(election_metadata_list)

@router.get(
    "/{election_name:str}",
    description="""
    Retrieves the election data for an election by name.
    Returns private details when the time is allowed.
    If user is an admin or elections officer, returns computing ids for each candidate as well.
    """
)
async def get_election(
    request: Request,
    db_session: database.DBSession,
    election_name: str,
):
    current_time = datetime.now()
    slugified_name = _slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {slugified_name} does not exist"
        )

    is_valid_user, _, _ = await _validate_user(request, db_session)
    if current_time >= election.datetime_start_voting or is_valid_user:

        election_json = election.private_details(current_time)
        all_nominations = await elections.crud.get_all_registrations_in_election(db_session, slugified_name)
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

def _raise_if_bad_election_data(
    name: str,
    election_type: str,
    datetime_start_nominations: datetime,
    datetime_start_voting: datetime,
    datetime_end_voting: datetime,
    available_positions: str | None,
):
    if election_type not in election_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unknown election type {election_type}",
        )
    elif not (
        (datetime_start_nominations <= datetime_start_voting)
        and (datetime_start_voting <= datetime_end_voting)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dates must be in order from earliest to latest",
        )
    elif available_positions is not None:
        for position in available_positions.split(","):
            if position not in OfficerPosition.position_list():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"unknown position found in position list {position}",
                )
    elif len(_slugify(name)) > elections.tables.MAX_ELECTION_SLUG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election slug {_slugify(name)} is too long",
        )

@router.post(
    "/{election_name:str}",
    description="Creates an election and places it in the database. Returns election json on success",
)
async def create_election(
    request: Request,
    db_session: database.DBSession,
    election_name: str,
    election_type: str,
    datetime_start_nominations: datetime,
    datetime_start_voting: datetime,
    datetime_end_voting: datetime,
    # allows None, which assigns it to the default
    available_positions: str | None = None,
    survey_link: str | None = None,
):
    # ensure that election name is not "list" as it will collide with endpoint
    if election_name == "list":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot use that election name",
        )

    if available_positions is None:
        if election_type == "general_election":
            available_positions = elections.tables.DEFAULT_POSITIONS_GENERAL_ELECTION
        elif election_type == "by_election":
            available_positions = elections.tables.DEFAULT_POSITIONS_BY_ELECTION
        elif election_type == "council_rep_election":
            available_positions = elections.tables.DEFAULT_POSITIONS_COUNCIL_REP_ELECTION
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid election type {election_type} for available positions"
            )
    slugified_name = _slugify(election_name)
    current_time = datetime.now()
    _raise_if_bad_election_data(
        election_name,
        election_type,
        datetime_start_nominations,
        datetime_start_voting,
        datetime_end_voting,
        available_positions,
    )

    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission",
            # TODO: is this header actually required?
            headers={"WWW-Authenticate": "Basic"},
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
            name = election_name,
            type = election_type,
            datetime_start_nominations = datetime_start_nominations,
            datetime_start_voting = datetime_start_voting,
            datetime_end_voting = datetime_end_voting,
            available_positions = available_positions,
            survey_link = survey_link
        )
    )
    await db_session.commit()

    election = await elections.crud.get_election(db_session, slugified_name)
    return JSONResponse(election.private_details(current_time))

@router.patch(
    "/{election_name:str}",
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
    election_name: str,
    election_type: str,
    datetime_start_nominations: datetime,
    datetime_start_voting: datetime,
    datetime_end_voting: datetime,
    available_positions: str,
    survey_link: str | None = None,
):
    slugified_name = _slugify(election_name)
    current_time = datetime.now()
    _raise_if_bad_election_data(
        election_name,
        election_type,
        datetime_start_nominations,
        datetime_start_voting,
        datetime_end_voting,
        available_positions,
    )

    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission",
            headers={"WWW-Authenticate": "Basic"},
        )
    elif await elections.crud.get_election(db_session, slugified_name) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {slugified_name} does not exist",
        )

    # NOTE: If you update available positions, people will still *technically* be able to update their
    # registrations, however they will not be returned in the results.
    await elections.crud.update_election(
        db_session,
        Election(
            slug = slugified_name,
            name = election_name,
            type = election_type,
            datetime_start_nominations = datetime_start_nominations,
            datetime_start_voting = datetime_start_voting,
            datetime_end_voting = datetime_end_voting,
            available_positions = available_positions,
            survey_link = survey_link
        )
    )
    await db_session.commit()

    election = await elections.crud.get_election(db_session, slugified_name)
    return JSONResponse(election.private_details(current_time))

@router.delete(
    "/{election_name:str}",
    description="Deletes an election from the database. Returns whether the election exists after deletion."
)
async def delete_election(
    request: Request,
    db_session: database.DBSession,
    election_name: str
):
    slugified_name = _slugify(election_name)
    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer permission",
            # TODO: is this header actually required?
            headers={"WWW-Authenticate": "Basic"},
        )

    await elections.crud.delete_election(db_session, slugified_name)
    await db_session.commit()

    old_election = await elections.crud.get_election(db_session, slugified_name)
    return JSONResponse({"success": old_election is None})

# registration ------------------------------------------------------------- #

@router.get(
    "/registration/{election_name:str}",
    description="get your election registration(s)"
)
async def get_election_registrations(
    request: Request,
    db_session: database.DBSession,
    election_name: str
):
    slugified_name = _slugify(election_name)
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to get election registrations"
        )

    if await elections.crud.get_election(db_session, slugified_name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    registration_list = await elections.crud.get_all_registrations(db_session, computing_id, slugified_name)
    if registration_list is None:
        return JSONResponse([])
    return JSONResponse([
        item.serializable_dict() for item in registration_list
    ])

@router.post(
    "/registration/{election_name:str}",
    description="register for a specific position in this election, but doesn't set a speech"
)
async def register_in_election(
    request: Request,
    db_session: database.DBSession,
    election_name: str,
    position: str
):
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to register in election"
        )
    if position not in OfficerPosition.position_list():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {position}"
    )

    if await elections.crud.get_nominee_info(db_session, computing_id) is None:
        # ensure that the user has a nominee info entry before allowing registration to occur.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="must have submitted nominee info before registering"
        )

    current_time = datetime.now()
    slugified_name = _slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )
    elif position not in election.available_positions.split(","):
        # NOTE: We only restrict creating a registration for a position that doesn't exist,
        # not updating or deleting one
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{position} is not available to register for in this election"
        )
    elif election.status(current_time) != elections.tables.STATUS_NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registrations can only be made during the nomination period"
        )
    elif await elections.crud.get_all_registrations(db_session, computing_id, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you are already registered in this election"
        )

    # TODO: associate specific elections officers with specific elections, then don't
    # allow any elections officer running an election to register for it

    await elections.crud.add_registration(db_session, NomineeApplication(
        computing_id=computing_id,
        nominee_election=slugified_name,
        position=position,
        speech=None
    ))
    await db_session.commit()

# @router.patch(
#     "/registration/{election_name:str}",
#     description="update your speech for a specific position for an election"
# )
# async def update_registration(
#     request: Request,
#     db_session: database.DBSession,
#     election_name: str,
#     position: str,
#     speech: str | None,
# ):
#     logged_in, _, computing_id = await is_logged_in(request, db_session)
#     if not logged_in:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="must be logged in to update election registration"
#         )
#     elif position not in OfficerPosition.position_list():
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"invalid position {position}"
#         )

#     current_time = datetime.now()
#     slugified_name = _slugify(election_name)
#     election = await elections.crud.get_election(db_session, slugified_name)
#     if election is None:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"election with slug {slugified_name} does not exist"
#         )
#     elif election.status(current_time) != elections.tables.STATUS_NOMINATIONS:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="speeches can only be updated during the nomination period"
#         )
#     elif not await elections.crud.get_all_registrations(db_session, computing_id, slugified_name):
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="you are not yet registered in this election"
#         )

#     await elections.crud.update_registration(db_session, NomineeApplication(
#         computing_id=computing_id,
#         nominee_election=slugified_name,
#         position=position,
#         speech=speech
#     ))
#     await db_session.commit()

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
    elif not await elections.crud.get_all_registrations(db_session, computing_id, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="you are not yet registered in this election"
        )

    await elections.crud.delete_registration(db_session, computing_id, slugified_name, position)
    await db_session.commit()

# nominee info ------------------------------------------------------------- #

@router.get(
    "/nominee/info",
    description="Nominee info is always publically tied to elections, so be careful!"
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

    return JSONResponse(nominee_info.as_serializable())

@router.put(
    "/nominee/info",
    description="Will create or update nominee info. Returns an updated copy of their nominee info."
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
    return JSONResponse(nominee_info.as_serializable())
