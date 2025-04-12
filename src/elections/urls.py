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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="no elections found"
        )

    current_time = datetime.now()
    election_metadata_list = [
        election.public_metadata(current_time)
        for election in election_list
    ]

    return JSONResponse(election_metadata_list)

@router.get(
    "/by_name/{election_name:str}",
    description="""
    Retrieves the election data for an election by name.
    Returns private details when the time is allowed.
    If user is an admin or elections officer, returns computing ids for each candidate as well.
    """
)
async def get_election(
    request: Request,
    db_session: database.DBSession,
    name: str,
):
    current_time = datetime.now()

    election = await elections.crud.get_election(db_session, _slugify(name))
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {_slugify(name)} does not exist"
        )

    is_valid_user, _, _ = await _validate_user(request, db_session)
    if current_time >= election.datetime_start_voting or is_valid_user:

        election_json = election.private_details(current_time)
        all_nominations = elections.crud.get_all_registrations_in_election(db_session, _slugify(name))
        election_json["candidates"] = []

        avaliable_positions_list = election.avaliable_positions.split(",")
        for nomination in all_nominations:
            if nomination.position not in avaliable_positions_list:
                # ignore any positions that are **no longer** active
                continue

            # NOTE: if a nominee does not input their legal name, they are not considered a nominee
            nominee_info = elections.crud.get_nominee_info(db_session, nomination.computing_id)
            if nominee_info is None:
                print("unreachable")
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
        return JSONResponse()
    else:
        election_json = election.public_details(current_time)

    return JSONResponse(election_json)

def _raise_if_bad_election_data(
    name: str,
    election_type: str,
    datetime_start_nominations: datetime,
    datetime_start_voting: datetime,
    datetime_end_voting: datetime,
    avaliable_positions: str | None,
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
    elif avaliable_positions is not None:
        for position in avaliable_positions.split(","):
            if position not in OfficerPosition.position_list():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"unknown position found in position list {position}",
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

@router.post(
    "/by_name/{election_name:str}",
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
    # allows None, which assigns it to the default
    avaliable_positions: str | None,
    survey_link: str | None,
):
    current_time = datetime.now()
    _raise_if_bad_election_data(
        name,
        election_type,
        datetime_start_nominations,
        datetime_start_voting,
        datetime_end_voting,
        avaliable_positions,
    )

    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission",
            # TODO: is this header actually required?
            headers={"WWW-Authenticate": "Basic"},
        )
    elif await elections.crud.get_election(db_session, _slugify(name)) is not None:
        # don't overwrite a previous election
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="would overwrite previous election",
        )

    if avaliable_positions is None:
        if election_type == "general_election":
            avaliable_positions = elections.tables.DEFAULT_POSITIONS_GENERAL_ELECTION
        elif election_type == "by_election":
            avaliable_positions = elections.tables.DEFAULT_POSITIONS_BY_ELECTION
        elif election_type == "council_rep_election":
            avaliable_positions = elections.tables.DEFAULT_POSITIONS_COUNCIL_REP_ELECTION
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"invalid election type {election_type} for avaliable positions"
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
            avaliable_positions = avaliable_positions,
            survey_link = survey_link
        )
    )
    await db_session.commit()

    election = await elections.crud.get_election(db_session, _slugify(name))
    return JSONResponse(election.private_details(current_time))

@router.patch(
    "/by_name/{election_name:str}",
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
    avaliable_positions: str,
    survey_link: str | None,
):
    current_time = datetime.now()
    _raise_if_bad_election_data(
        name,
        election_type,
        datetime_start_nominations,
        datetime_start_voting,
        datetime_end_voting,
        avaliable_positions,
    )

    is_valid_user, _, _ = await _validate_user(request, db_session)
    if not is_valid_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must have election officer or admin permission",
            headers={"WWW-Authenticate": "Basic"},
        )
    elif await elections.crud.get_election(db_session, _slugify(name)) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {_slugify(name)} does not exist",
        )

    # NOTE: If you update avaliable positions, people will still *technically* be able to update their
    # registrations, however they will not be returned in the results.
    await elections.crud.update_election(
        db_session,
        Election(
            slug = _slugify(name),
            name = name,
            type = election_type,
            datetime_start_nominations = datetime_start_nominations,
            datetime_start_voting = datetime_start_voting,
            datetime_end_voting = datetime_end_voting,
            avaliable_positions = avaliable_positions,
            survey_link = survey_link
        )
    )
    await db_session.commit()

    election = await elections.crud.get_election(db_session, _slugify(name))
    return JSONResponse(election.private_details(current_time))

@router.delete(
    "/by_name/{election_name:str}",
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

@router.get(
    "/register/{election_name:str}",
    description="get your election registration(s)"
)
async def get_election_registrations(
    request: Request,
    db_session: database.DBSession,
    election_name: str
):
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to get election registrations"
        )

    election_slug = _slugify(election_name)
    if await elections.crud.get_election(db_session, election_slug) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {election_slug} does not exist"
        )

    registration_list = await elections.crud.get_all_registrations(db_session, computing_id, election_slug)
    if registration_list is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you are already registered in this election"
        )

    return JSONResponse([
        item.serializable_dict() for item in registration_list
    ])

@router.post(
    "/register/{election_name:str}",
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
    elif position not in OfficerPosition.position_list():
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
    election_slug = _slugify(election_name)
    election = await elections.crud.get_election(db_session, election_slug)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {election_slug} does not exist"
        )
    elif position not in election.avaliable_positions.split(","):
        # NOTE: We only restrict creating a registration for a position that doesn't exist,
        # not updating or deleting one
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{position} is not avaliable to register for in this election"
        )
    elif election.status(current_time) != elections.tables.STATUS_NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registrations can only be made during the nomination period"
        )
    elif await elections.crud.get_all_registrations(db_session, computing_id, election_slug) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you are already registered in this election"
        )

    # TODO: associate specific elections officers with specific elections, then don't
    # allow any elections officer running an election to register for it

    await elections.crud.add_registration(db_session, NomineeApplication(
        computing_id=computing_id,
        nominee_election=election_slug,
        position=position,
        speech=None
    ))
    await db_session.commit()

@router.patch(
    "/register/{election_name:str}",
    description="update your speech for a specific position for an election"
)
async def update_registration(
    request: Request,
    db_session: database.DBSession,
    election_name: str,
    position: str,
    speech: str | None,
):
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to update election registration"
        )
    elif position not in OfficerPosition.position_list():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {position}"
        )

    current_time = datetime.now()
    election_slug = _slugify(election_name)
    election = await elections.crud.get_election(db_session, election_slug)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {election_slug} does not exist"
        )
    elif election.status(current_time) != elections.tables.STATUS_NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="speeches can only be updated during the nomination period"
        )
    elif await elections.crud.get_all_registrations(db_session, computing_id, election_slug) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you are not yet registered in this election"
        )

    await elections.crud.update_registration(db_session, NomineeApplication(
        computing_id=computing_id,
        nominee_election=election_slug,
        position=position,
        speech=speech
    ))
    await db_session.commit()

@router.delete(
    "/register/{election_name:str}",
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
            detail="must be logged in to delete election registeration"
        )
    elif position not in OfficerPosition.position_list():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {position}"
        )

    current_time = datetime.now()
    election_slug = _slugify(election_name)
    election = await elections.crud.get_election(db_session, election_slug)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"election with slug {election_slug} does not exist"
        )
    elif election.status(current_time) != elections.tables.STATUS_NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registration can only be revoked during the nomination period"
        )
    elif await elections.crud.get_all_registrations(db_session, computing_id, election_slug) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="you are not yet registered in this election"
        )

    await elections.crud.delete_registration(db_session, computing_id, election_slug, position)
    await db_session.commit()

# nominee info ------------------------------------------------------------- #

@router.get(
    "/nominee_info",
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

@router.patch(
    "/nominee_info",
    description="Will create or update nominee info. Returns an updated copy of their nominee info."
)
async def provide_nominee_info(
    request: Request,
    db_session: database.DBSession,
    full_name: str,
    linked_in: str | None,
    instagram: str | None,
    email: str | None,
    discord_username: str | None,
):
    logged_in, _, computing_id = await is_logged_in(request, db_session)
    if not logged_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in to update nominee info"
        )

    pending_nominee_info = NomineeInfo(
        computing_id = computing_id,
        full_name = full_name,
        linked_in = linked_in,
        instagram = instagram,
        email = email,
        discord_username = discord_username,
    )
    if await elections.crud.get_nominee_info(db_session, computing_id) is None:
        await elections.crud.create_nominee_info(db_session, pending_nominee_info)
    else:
        await elections.crud.update_nominee_info(db_session, pending_nominee_info)

    await db_session.commit()

    new_nominee_info = await elections.crud.get_nominee_info(db_session, computing_id)
    return JSONResponse(new_nominee_info.as_serializable())
