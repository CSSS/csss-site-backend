import logging
from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

import auth.crud
import database
import officers.crud
import utils
from constants import COMPUTING_ID_MAX
from officers.constants import OfficerPosition
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import OfficerInfoUpload, OfficerTermUpload
from permission.types import OfficerPrivateInfo, WebsiteAdmin

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

# ---------------------------------------- #
# checks

async def has_officer_private_info_access(
    request: Request,
    db_session: database.DBSession
) -> tuple[None | str, None | str, bool]:
    """determine if the user has access to private officer info"""
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        return None, None, False

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if computing_id is None:
        return session_id, None, False

    has_private_access = await OfficerPrivateInfo.has_permission(db_session, computing_id)
    return session_id, computing_id, has_private_access

async def logged_in_or_raise(
    request: Request,
    db_session: database.DBSession
) -> tuple[str, str]:
    """gets the user's computing_id, or raises an exception if the current request is not logged in"""
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401)

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if session_computing_id is None:
        raise HTTPException(status_code=401)

    return session_id, session_computing_id

# ---------------------------------------- #
# endpoints

@router.get(
    "/current",
    description="Get information about all the officers. More information is given if you're authenticated & have access to private executive data.",
)
async def current_officers(
    # the request headers
    request: Request,
    db_session: database.DBSession,
):
    _, _, has_private_access = await has_officer_private_info_access(request, db_session)
    current_officers = await officers.crud.current_officers(db_session, has_private_access)
    return JSONResponse({
        position: [
            officer_data.serializable_dict()
            for officer_data in officer_data_list
        ]
        for position, officer_data_list in current_officers.items()
    })

@router.get(
    "/all",
    description="Information for all execs from all exec terms"
)
async def all_officers(
    request: Request,
    db_session: database.DBSession,
    # Officer terms for officers which have not yet started their term yet are considered private,
    # and may only be accessed by that officer and executives. All other officer terms are public.
    include_future_terms: bool = False,
):
    _, computing_id, has_private_access = await has_officer_private_info_access(request, db_session)
    if include_future_terms:
        is_website_admin = (computing_id is not None) and (await WebsiteAdmin.has_permission(db_session, computing_id))
        if not is_website_admin:
            raise HTTPException(status_code=401, detail="only website admins can view all executive terms that have not started yet")

    all_officers = await officers.crud.all_officers(db_session, has_private_access, include_future_terms)
    return JSONResponse([
        officer_data.serializable_dict()
        for officer_data in all_officers
    ])

@router.get(
    "/terms/{computing_id}",
    description="""Get term info for an executive. All term info is public for all past or active terms.""",
)
async def get_officer_terms(
    request: Request,
    db_session: database.DBSession,
    computing_id: str,
    include_future_terms: bool = False
):
    # TODO: should this be login-required if a user does not want to include future terms? The info is
    # supposed to all be public
    _, session_computing_id = await logged_in_or_raise(request, db_session)

    if (
        computing_id != session_computing_id
        and include_future_terms
    ):
        await WebsiteAdmin.has_permission_or_raise(db_session, session_computing_id)

    # all term info is public, so anyone can get any of it
    officer_terms = await officers.crud.get_officer_terms(
        db_session,
        computing_id,
        include_future_terms
    )
    return JSONResponse([
        term.serializable_dict() for term in officer_terms
    ])

@router.get(
    "/info/{computing_id}",
    description="Get officer info for the current user, if they've ever been an exec. Only admins can get info about another user.",
)
async def get_officer_info(
    request: Request,
    db_session: database.DBSession,
    computing_id: str,
):
    _, session_computing_id = await logged_in_or_raise(request, db_session)

    if computing_id != session_computing_id:
        await WebsiteAdmin.has_permission_or_raise(
            db_session, session_computing_id,
            errmsg="must have website admin permissions to get officer info about another user"
        )

    officer_info = await officers.crud.get_officer_info(db_session, computing_id)
    if officer_info is None:
        # this will be triggered if a non-officer calls the endpoint
        raise HTTPException(status_code=404, detail="user has no officer info")

    return JSONResponse(officer_info.serializable_dict())

# TODO: move this to types?
@dataclass
class InitialOfficerInfo:
    computing_id: str
    position: str
    start_date: date

    def valid_or_raise(self):
        if len(self.computing_id) > COMPUTING_ID_MAX:
            raise HTTPException(status_code=400, detail=f"computing_id={self.computing_id} is too large")
        elif self.computing_id == "":
            raise HTTPException(status_code=400, detail="computing_id cannot be empty")
        elif self.position not in OfficerPosition.position_list():
            raise HTTPException(status_code=400, detail=f"invalid position={self.position}")

@router.post(
    "/term",
    description="""
        Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA.
        Updates the system with a new officer, and enables the user to login to the system to input their information.
    """,
)
async def new_officer_term(
    request: Request,
    db_session: database.DBSession,
    officer_info_list: list[InitialOfficerInfo] = Body(), # noqa: B008
):
    """
    If the current computing_id is not already an officer, officer_info will be created for them.
    """
    for officer_info in officer_info_list:
        officer_info.valid_or_raise()

    _, session_computing_id = logged_in_or_raise(request, db_session)
    await WebsiteAdmin.has_permission_or_raise(db_session, session_computing_id)

    for officer_info in officer_info_list:
        await officers.crud.create_new_officer_info(db_session, OfficerInfo(
            computing_id = officer_info.computing_id,
            # TODO: use sfu api to get legal name from officer_info.computing_id
            legal_name = "default name",
            phone_number = None,

            discord_id = None,
            discord_name = None,
            discord_nickname = None,

            google_drive_email = None,
            github_username = None,
        ))
        await officers.crud.create_new_officer_term(db_session, OfficerTerm(
            computing_id = officer_info.computing_id,
            position = officer_info.position,
            # TODO: remove the hours & seconds (etc.) from start_date
            # TODO: start_date should be a Date, not a Datetime
            start_date = officer_info.start_date,
        ))

    await db_session.commit()
    return PlainTextResponse("success")

@router.patch(
    "/info/{computing_id}",
    description="""
        After elections, officer computing ids are input into our system.
        If you have been elected as a new officer, you may authenticate with SFU CAS,
        then input your information & the valid token for us. Admins may update this info.
    """
)
async def update_info(
    request: Request,
    db_session: database.DBSession,
    computing_id: str,
    officer_info_upload: OfficerInfoUpload = Body() # noqa: B008
):
    officer_info_upload.valid_or_raise()
    _, session_computing_id = logged_in_or_raise(request, db_session)

    if computing_id != session_computing_id:
        await WebsiteAdmin.has_permission_or_raise(
            db_session, session_computing_id,
            errmsg="must have website admin permissions to update another user"
        )

    old_officer_info = await officers.crud.get_officer_info(db_session, computing_id)
    validation_failures, corrected_officer_info = await officer_info_upload.validate(computing_id, old_officer_info)

    # TODO (#27): log all important changes just to a .log file & persist them for a few years

    success = await officers.crud.update_officer_info(db_session, corrected_officer_info)
    if not success:
        raise HTTPException(status_code=400, detail="officer_info does not exist yet, please create the officer info entry first")

    await db_session.commit()

    updated_officer_info = await officers.crud.get_officer_info(db_session, computing_id)
    return JSONResponse({
        "officer_info": updated_officer_info.serializable_dict(),
        "validation_failures": validation_failures,
    })

@router.patch(
    "/term/{term_id}",
    description=""
)
async def update_term(
    request: Request,
    db_session: database.DBSession,
    term_id: int,
    officer_term_upload: OfficerTermUpload = Body(), # noqa: B008
):
    officer_term_upload.valid_or_raise()
    _, session_computing_id = logged_in_or_raise(request, db_session)

    old_officer_term = await officers.crud.get_officer_term_by_id(db_session, term_id)
    if old_officer_term.computing_id != session_computing_id:
        await WebsiteAdmin.has_permission_or_raise(
            db_session, session_computing_id,
            errmsg="must have website admin permissions to update another user"
        )
    elif utils.is_past_term(old_officer_term):
        await WebsiteAdmin.has_permission_or_raise(
            db_session, session_computing_id,
            errmsg="only website admins can update past terms"
        )

    if (
        officer_term_upload.position != old_officer_term.position
        or officer_term_upload.start_date != old_officer_term.start_date.date()
        or officer_term_upload.end_date != old_officer_term.end_date.date()
    ):
        await WebsiteAdmin.has_permission_or_raise(
            db_session, session_computing_id,
            errmsg="only admins can write new versions of position, start_date, and end_date"
        )

    if officer_term_upload.position != old_officer_term.position:
        # TODO: update the end_date here
        pass

    # TODO (#27): log all important changes to a .log file
    success = await officers.crud.update_officer_term(
        db_session,
        officer_term_upload.to_officer_term(term_id, old_officer_term.computing_id)
    )
    if not success:
        raise HTTPException(status_code=400, detail="the associated officer_term does not exist yet, please create it first")

    await db_session.commit()

    new_officer_term = await officers.crud.get_officer_term_by_id(db_session, term_id)
    return JSONResponse({
        "officer_term": new_officer_term.serializable_dict(),
        "validation_failures": [], # none for now, but may be important later
    })

# TODO: test this endpoint
@router.delete(
    "/term/{term_id}",
    description="Remove the specified officer term. Only website admins can run this endpoint. BE CAREFUL WITH THIS!",
)
async def remove_officer(
    request: Request,
    db_session: database.DBSession,
    term_id: int,
):
    _, session_computing_id = logged_in_or_raise(request, db_session)
    await WebsiteAdmin.has_permission_or_raise(
        db_session, session_computing_id,
        errmsg="must have website admin permissions to remove a term"
    )

    deleted_officer_term = await officers.crud.get_officer_term_by_id(db_session, term_id)

    # TODO (#27): log all important changes to a .log file
    await officers.crud.delete_officer_term_by_id(db_session, term_id)

    return JSONResponse({
        "officer_term": deleted_officer_term.serializable_dict(),
    })
