import logging
from dataclasses import dataclass
from datetime import date, datetime

import auth.crud
import database
import github
import sqlalchemy
import utils
from constants import COMPUTING_ID_MAX
from discord import discord
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from permission.types import OfficerPrivateInfo, WebsiteAdmin

import officers.crud
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import OfficerInfoUpload, OfficerTermUpload

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

# TODO: combine the following two endpoints
@router.get(
    "/current",
    description="Get information about all the officers. More information is given if you're authenticated & have access to private executive data.",
)
async def current_officers(
    # the request headers
    request: Request,
    db_session: database.DBSession,
):
    # determine if the user has access to this private data
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        has_private_access = False
    else:
        computing_id = await auth.crud.get_computing_id(db_session, session_id)
        has_private_access = await OfficerPrivateInfo.has_permission(db_session, computing_id)

    current_executives = await officers.crud.current_executive_team(db_session, has_private_access)
    json_current_executives = {
        position: [
            officer_data.serializable_dict() for officer_data in officer_data_list
        ] for position, officer_data_list in current_executives.items()
    }

    return JSONResponse(json_current_executives)

@router.get(
    "/all",
    description="Information from all exec terms. If year is not included, all years will be returned. If semester is not included, all semesters that year will be returned. If semester is given, but year is not, return all years and all semesters.",
)
async def all_officers(
    request: Request,
    db_session: database.DBSession,
    view_only_filled_in: bool = True,
):
    async def has_access(db_session: database.DBSession, request: Request) -> bool:
        # determine if user has access to this private data
        session_id = request.cookies.get("session_id", None)
        if session_id is None:
            return False

        computing_id = await auth.crud.get_computing_id(db_session, session_id)
        if computing_id is None:
            return False
        else:
            has_private_access = await OfficerPrivateInfo.has_permission(db_session, computing_id)
            is_website_admin = await WebsiteAdmin.has_permission(db_session, computing_id)

            if not view_only_filled_in and (session_id is None or not is_website_admin):
                raise HTTPException(status_code=401, detail="must have private access to view not filled in terms")

            return has_private_access

    has_private_access = await has_access(db_session, request)

    all_officer_data = await officers.crud.all_officer_terms(db_session, has_private_access, view_only_filled_in)
    all_officer_data = [officer_data.serializable_dict() for officer_data in all_officer_data]
    return JSONResponse(all_officer_data)

@router.get(
    "/terms/{computing_id}",
    description="Get term info for an executive. Private info will be provided if you have permissions.",
)
async def get_officer_terms(
    request: Request,
    db_session: database.DBSession,
    computing_id: str,
    # the maximum number of terms to return, in chronological order
    max_terms: None | int = 1,
    # TODO: implement the following
    # view_only_filled_in: bool = True,
):
    # all term info is public, so anyone can get any of it
    officer_terms = await officers.crud.officer_terms(db_session, computing_id, max_terms, hide_filled_in=True)
    return JSONResponse([term.serializable_dict() for term in officer_terms])

# TODO: make this into getting info for any computing_id?
@router.get(
    "/my_info",
    description="Get officer info for the current user, if they've ever been an exec.",
)
async def get_officer_info(
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401)

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if computing_id is None:
        raise HTTPException(status_code=401)

    officer_info = await officers.crud.officer_info(db_session, computing_id)
    if officer_info is None:
        raise HTTPException(status_code=404, detail="user has no officer info")

    return JSONResponse(officer_info.serializable_dict())

@dataclass
class InitialOfficerInfo:
    computing_id: str
    position: str
    start_date: date

@router.post(
    "/term",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Updates the system with a new officer, and enables the user to login to the system to input their information.",
)
async def new_officer_term(
    request: Request,
    db_session: database.DBSession,
    officer_info_list: list[InitialOfficerInfo] = Body(),  # noqa: B008
):
    """
    If the current computing_id is not already an officer, officer_info will be created for them.
    """
    for officer_info in officer_info_list:
        if len(officer_info.computing_id) > COMPUTING_ID_MAX:
            raise HTTPException(status_code=400, detail=f"computing_id={officer_info.computing_id} is too large")
        elif officer_info.position not in OfficerPosition.position_values():
            raise HTTPException(status_code=400, detail=f"invalid position={officer_info.position}")

    WebsiteAdmin.validate_request(db_session, request)

    for officer_info in officer_info_list:
        # TODO: fix a bug with this stuff & test inserting & viewing mutliple executives
        await officers.crud.create_new_officer_info(
            db_session,
            # TODO: do I need this object atm?
            OfficerInfoUpload(
                # TODO: use sfu api to get legal name
                legal_name = "default name",
            ).to_officer_info(officer_info.computing_id, None, None),
        )
        # TODO: update create_new_officer_term to be the same as create_new_officer_info
        success = await officers.crud.create_new_officer_term(db_session, OfficerTermUpload(
            computing_id = officer_info.computing_id,
            position = officer_info.position,
            # TODO: remove the hours & seconds (etc.) from start_date
            start_date = officer_info.start_date,
        ).to_officer_term())
        if not success:
            raise HTTPException(status_code=400, detail="Officer term already exists, no changes made")

    await db_session.commit()
    return PlainTextResponse("ok")

@router.patch(
    "/info/{computing_id}",
    description=(
        "After elections, officer computing ids are input into our system. "
        "If you have been elected as a new officer, you may authenticate with SFU CAS, "
        "then input your information & the valid token for us. Admins may update this info."
    ),
)
# TODO: computing_id in all paths
async def update_info(
    request: Request,
    db_session: database.DBSession,
    computing_id: str,
    officer_info_upload: OfficerInfoUpload = Body(), # noqa: B008
):
    http_exception = officer_info_upload.validate()
    if http_exception is not None:
        raise http_exception

    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="must be logged in")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if (
        computing_id != session_computing_id
        and not await WebsiteAdmin.has_permission(db_session, session_computing_id)
    ):
        # the current user can only input the info for another user if they have permissions
        raise HTTPException(status_code=401, detail="must have website admin permissions to update another user")

    # TODO: log all important changes just to a .log file

    old_officer_info = await officers.crud.officer_info(db_session, computing_id)
    new_officer_info = officer_info_upload.to_officer_info(
        computing_id=computing_id,
        discord_id=None,
        discord_nickname=None,
    )

    # TODO: turn this into a function
    validation_failures = []

    if not utils.is_valid_phone_number(officer_info_upload.phone_number):
        validation_failures += [f"invalid phone number {officer_info_upload.phone_number}"]
        new_officer_info.phone_number = old_officer_info.phone_number

    if officer_info_upload.discord_name is None or officer_info_upload.discord_name == "":
        new_officer_info.discord_name = None
        new_officer_info.discord_id = None
        new_officer_info.discord_nickname = None
    else:
        discord_user_list = await discord.search_username(officer_info_upload.discord_name)
        if discord_user_list == []:
            validation_failures += [f"unable to find discord user with the name {officer_info_upload.discord_name}"]
            new_officer_info.discord_name = old_officer_info.discord_name
            new_officer_info.discord_id = old_officer_info.discord_id
            new_officer_info.discord_nickname = old_officer_info.discord_nickname
        elif len(discord_user_list) > 1:
            validation_failures += [f"too many discord users start with {officer_info_upload.discord_name}"]
            new_officer_info.discord_name = old_officer_info.discord_name
            new_officer_info.discord_id = old_officer_info.discord_id
            new_officer_info.discord_nickname = old_officer_info.discord_nickname
        else:
            discord_user = discord_user_list[0]
            new_officer_info.discord_name = discord_user.username
            new_officer_info.discord_id = discord_user.id
            new_officer_info.discord_nickname = (
                discord_user.global_name
                if discord_user.global_name is not None
                else discord_user.username
            )

    # TODO: validate google-email using google module, by trying to assign the user to a permission or something
    if not utils.is_valid_email(officer_info_upload.google_drive_email):
        validation_failures += [f"invalid email format {officer_info_upload.google_drive_email}"]
        new_officer_info.google_drive_email = old_officer_info.google_drive_email

    # validate github user is real
    if await github.internals.get_user_by_username(officer_info_upload.github_username) is None:
        validation_failures += [f"invalid github username {officer_info_upload.github_username}"]
        new_officer_info.github_username = old_officer_info.github_username

    # TODO: invite github user
    # TODO: detect if changing github username & uninvite old user

    success = await officers.crud.update_officer_info(db_session, new_officer_info)
    if not success:
        raise HTTPException(status_code=400, detail="officer_info does not exist yet, please create the officer info entry first")

    await db_session.commit()

    updated_officer_info = await officers.crud.officer_info(db_session, computing_id)
    return JSONResponse({
        "updated_officer_info": updated_officer_info.serializable_dict(),
        "validation_failures": validation_failures,
    })

@router.patch(
    "/term/{term_id}",
)
async def update_term(
    request: Request,
    db_session: database.DBSession,
    term_id: int,
    officer_term_upload: OfficerTermUpload = Body(), # noqa: B008
):
    http_exception = officer_term_upload.validate()
    if http_exception is not None:
        raise http_exception

    # Refactor all of these gets & raises into small functions
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="must be logged in")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if (
        officer_term_upload.computing_id != session_computing_id
        and not await WebsiteAdmin.has_permission(db_session, session_computing_id)
    ):
        # the current user can only input the info for another user if they have permissions
        raise HTTPException(status_code=401, detail="must have website admin permissions to update another user")

    old_officer_info = await officers.crud.officer_term(db_session, term_id)

    # NOTE: Only admins can write new versions of position, start_date, and end_date.
    if (
        (
            officer_term_upload.position != old_officer_info.position
            or officer_term_upload.start_date != old_officer_info.start_date
            or officer_term_upload.end_date != old_officer_info.end_date
        )
        and not await WebsiteAdmin.has_permission(db_session, session_computing_id)
    ):
        raise HTTPException(status_code=401, detail="Non-admins cannot modify position, start_date, or end_date.")

    # NOTE: An officer can change their own data for terms that are ongoing.
    if officer_term_upload.position not in OfficerPosition.position_list():
        raise HTTPException(status_code=400, detail=f"invalid new position={officer_term_upload.position}")
    elif officer_term_upload.end_date is not None and officer_term_upload.start_date > officer_term_upload.end_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # TODO: log all important changes just to a .log file
    success = await officers.crud.update_officer_term(db_session, old_officer_info)
    if not success:
        raise HTTPException(status_code=400, detail="the associated officer_term does not exist yet, please create it first")

    await db_session.commit()

    new_officer_term = await officers.crud.officer_term(db_session, term_id)
    return JSONResponse({
        "updated_officer_term": new_officer_term.serializable_dict(),
        "validation_failures": [], # none for now, but may be important later
    })

"""
# TODO: test this error later
@router.get("/please_error", description="Raises an error & should send an email to the sysadmin")
async def raise_error():
    raise ValueError("This is an error, you're welcome")

@router.post(
    "/remove",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Removes the officer from the system entirely. BE CAREFUL WITH THIS OPTION aaaaaaaaaaaaaaaaaa.",
)
async def remove_officer():
    return {}
"""
