import logging
from dataclasses import dataclass
from datetime import date, datetime

import auth.crud
import database
from constants import COMPUTING_ID_MAX
from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from permission.types import OfficerPrivateInfo, WebsiteAdmin
from utils import is_iso_format

import officers.crud
from officers.constants import OfficerPosition
from officers.types import OfficerInfoData, OfficerTermData

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

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
    # determine if user has access to this private data
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        has_private_access = False

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    has_private_access = await OfficerPrivateInfo.has_permission(db_session, computing_id)

    is_website_admin = await WebsiteAdmin.has_permission(db_session, computing_id)
    if (
        not view_only_filled_in
        and (session_id is None or not is_website_admin)
    ):
        raise HTTPException(status_code=401, detail="must have private access to view not filled in terms")

    all_officer_terms = await officers.crud.all_officer_terms(db_session, has_private_access, view_only_filled_in)
    all_officer_terms = [
        officer_data.serializable_dict() for officer_data in all_officer_terms
    ]

    return JSONResponse(all_officer_terms)

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
):
    # TODO: we should check computing_id & stuff & return an exception
    officer_terms = await officers.crud.officer_terms(db_session, computing_id, max_terms, hide_filled_in=True)
    return JSONResponse([term.serializable_dict() for term in officer_terms])

@dataclass
class InitialOfficerInfo:
    computing_id: str
    position: str
    start_date: date

@router.post(
    "/new_term",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Updates the system with a new officer, and enables the user to login to the system to input their information.",
)
async def new_officer_term(
    request: Request,
    db_session: database.DBSession,
    # TODO: minimize number of transactions, so we can fail more easily
    officer_info_list: list[InitialOfficerInfo] = Body(),  # noqa: B008
):
    """
    If the current computing_id is not already an officer, officer_info will be created for them.
    """
    for officer_info in officer_info_list:
        if len(officer_info.computing_id) > COMPUTING_ID_MAX:
            raise HTTPException(status_code=400, detail=f"computing_id={officer_info.computing_id} is too large")
        elif officer_info.position not in OfficerPosition.__members__.values():
            raise HTTPException(status_code=400, detail=f"invalid position={officer_info.position}")
        elif not is_iso_format(officer_info.start_date):
            raise HTTPException(status_code=400, detail=f"start_date={officer_info.start_date} must be a valid iso date")

    WebsiteAdmin.validate_request(db_session, request)

    for officer_info in officer_info_list:
        officers.crud.create_new_officer_info(db_session, OfficerInfoData(
            computing_id = officer_info.computing_id,
        ))
        success = officers.crud.create_new_officer_term(db_session, OfficerTermData(
            computing_id = officer_info.computing_id,
            position = officer_info.position,
            # TODO: remove the hours & seconds (etc.) from start_date
            start_date = officer_info.start_date,
        ))
        if not success:
            raise HTTPException(status_code=400, detail="Officer term already exists, no changes made")

    await db_session.commit()
    return PlainTextResponse("ok")

@router.post(
    "/update_info",
    description=(
        "After elections, officer computing ids are input into our system. "
        "If you have been elected as a new officer, you may authenticate with SFU CAS, "
        "then input your information & the valid token for us. Admins may update this info."
    ),
)
async def update_info(
    request: Request,
    db_session: database.DBSession,
    officer_info: OfficerInfoData = Body(), # noqa: B008
):
    # TODO: can computing_id be null or non-string?
    http_exception = officer_info.validate()
    if http_exception is not None:
        raise http_exception

    # TODO: make this a utility? (need a naming convention for functions which can raise exceptions)
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="must be logged in")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if (
        officer_info.computing_id != session_computing_id
        and not await WebsiteAdmin.has_permission(db_session, session_computing_id)
    ):
        # the current user can only input the info for another user if they have permissions
        raise HTTPException(status_code=401, detail="must have website admin permissions to update another user")

    # TODO: if current user has admin permission, log this change

    success = await officers.crud.update_officer_info(db_session, officer_info)
    if not success:
        raise HTTPException(status_code=400, detail="officer_info does not exist yet, please create the officer info entry first")

    await db_session.commit()
    return PlainTextResponse("ok")

@router.post(
    "/update_term",
)
async def update_term(
    request: Request,
    db_session: database.DBSession,
    # TODO: ensure the dates don't have seconds / hours as they're passed in
    officer_term: OfficerTermData = Body(), # noqa: B008
):
    # TODO: can computing_id be null or non-string?
    http_exception = officer_term.validate()
    if http_exception is not None:
        raise http_exception

    # TODO: make this a utility? (need a naming convention for functions which can raise exceptions)
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="must be logged in")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if (
        officer_term.computing_id != session_computing_id
        and not await WebsiteAdmin.has_permission(db_session, session_computing_id)
    ):
        # the current user can only input the info for another user if they have permissions
        raise HTTPException(status_code=401, detail="must have website admin permissions to update another user")

    # TODO: if current user has admin permission, log this change

    success = await officers.crud.update_officer_term(db_session, officer_term)
    if not success:
        raise HTTPException(status_code=400, detail="the associated officer_term does not exist yet, please create the associated officer term")

    await db_session.commit()
    return PlainTextResponse("ok")


"""
# TODO: test this error later
@router.get("/please_error", description="Raises an error & should send an email to the sysadmin")
async def raise_error():
    raise ValueError("This is an error, you're welcome")

@router.get(
    "/my_info",
    description="Get info about whether you are still an executive or not / what your position is.",
)
async def my_info():
    return {}

@router.post(
    "/remove",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Removes the officer from the system entirely. BE CAREFUL WITH THIS OPTION aaaaaaaaaaaaaaaaaa.",
)
async def remove_officer():
    return {}
"""
