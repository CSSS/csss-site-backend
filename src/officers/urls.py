from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

import auth.crud
import database
import officers.crud
import utils
from officers.models import (
    OfficerInfoResponse,
    OfficerSelfUpdate,
    OfficerTermCreate,
    OfficerTermResponse,
    OfficerTermUpdate,
    OfficerUpdate,
)
from officers.tables import OfficerInfo, OfficerTerm
from permission.types import OfficerPrivateInfo, WebsiteAdmin
from utils.shared_models import DetailModel, SuccessResponse
from utils.urls import admin_or_raise, is_website_admin, logged_in_or_raise

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

# ---------------------------------------- #
# checks

async def _has_officer_private_info_access(
    request: Request,
    db_session: database.DBSession
) -> tuple[bool, str | None,]:
    """determine if the user has access to private officer info"""
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        return False, None

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if computing_id is None:
        return False, None

    has_private_access = await OfficerPrivateInfo.has_permission(db_session, computing_id)
    return has_private_access, computing_id

# ---------------------------------------- #
# endpoints

@router.get(
    "/current",
    description="Get information about the current officers. With no authorization, only get basic info.",
    response_model=list[OfficerInfoResponse],
    operation_id="get_current_officers"
)
async def current_officers(
    request: Request,
    db_session: database.DBSession,
):
    has_private_access, _ = await _has_officer_private_info_access(request, db_session)
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
    description="Information for all execs from all exec terms",
    response_model=list[OfficerInfoResponse],
    responses={
        403: { "description": "not authorized to view private info", "model": DetailModel }
    },
    operation_id="get_all_officers"
)
async def all_officers(
    request: Request,
    db_session: database.DBSession,
    # Officer terms for officers which have not yet started their term yet are considered private,
    # and may only be accessed by that officer and executives. All other officer terms are public.
    include_future_terms: bool = False,
):
    has_private_access, computing_id = await _has_officer_private_info_access(request, db_session)
    if include_future_terms:
        is_website_admin = (computing_id is not None) and (await WebsiteAdmin.has_permission(db_session, computing_id))
        if not is_website_admin:
            raise HTTPException(status_code=401, detail="only website admins can view all executive terms that have not started yet")

    all_officers = await officers.crud.all_officers(db_session, include_future_terms)
    exclude = {
        "discord_id",
        "discord_name",
        "discord_nickname",
        "computing_id",
        "phone_number",
        "github_username",
        "google_drive_email",
        "photo_url"
    } if not has_private_access else {}

    return JSONResponse(content=[
        officer_data.model_dump(exclude=exclude, mode="json")
        for officer_data in all_officers
    ])

@router.get(
    "/terms/{computing_id}",
    description="""
        Get term info for an executive. All term info is public for all past or active terms.
        Future terms can only be accessed by website admins.
    """,
    response_model=list[OfficerTermResponse],
    responses={
        401: { "description": "not authorized to view private info", "model": DetailModel }
    },
    operation_id="get_officer_terms_by_id"
)
async def get_officer_terms(
    request: Request,
    db_session: database.DBSession,
    computing_id: str,
    include_future_terms: bool = False
):
    if include_future_terms:
        _, session_computing_id = await logged_in_or_raise(request, db_session)
        if computing_id != session_computing_id:
            await WebsiteAdmin.has_permission_or_raise(db_session, session_computing_id)

    # all term info is public, so anyone can get any of it
    officer_terms = await officers.crud.get_officer_terms(
        db_session,
        computing_id,
        include_future_terms
    )
    return JSONResponse([
        OfficerTermResponse.model_validate(term) for term in officer_terms
    ])

@router.get(
    "/info/{computing_id:str}",
    description="Get officer info for the current user, if they've ever been an exec. Only admins can get info about another user.",
    response_model=OfficerInfoResponse,
    responses={
        403: { "description": "not authorized to view author user info", "model": DetailModel }
    },
    operation_id="get_officer_info_by_id"
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

    officer_info = await officers.crud.get_officer_info_or_raise(db_session, computing_id)
    return JSONResponse(officer_info.serializable_dict())

@router.post(
    "/term",
    description="""
        Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA.
        Updates the system with a new officer, and enables the user to login to the system to input their information.
    """,
    response_model=SuccessResponse,
    responses={
        403: { "description": "must be a website admin", "model": DetailModel },
        500: { "model": DetailModel },
    },
    operation_id="create_officer_term"
)
async def new_officer_term(
    request: Request,
    db_session: database.DBSession,
    officer_info_list: list[OfficerTermCreate],
):
    await admin_or_raise(request, db_session)

    for officer_info in officer_info_list:
        # if user with officer_info.computing_id has never logged into the website before,
        # a site_user tuple will be created for them.
        await officers.crud.create_new_officer_info(db_session, OfficerInfo(
            computing_id = officer_info.computing_id,
            # TODO (#71): use sfu api to get legal name from officer_info.computing_id
            legal_name = officer_info.legal_name,
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
            start_date = officer_info.start_date,
        ))

    await db_session.commit()
    return JSONResponse({ "success": True })

@router.patch(
    "/info/{computing_id:str}",
    description="""
        After election, officer computing ids are input into our system.
        If you have been elected as a new officer, you may authenticate with SFU CAS,
        then input your information & the valid token for us. Admins may update this info.
    """,
    response_model=OfficerInfoResponse,
    responses={
        403: { "description": "must be a website admin", "model": DetailModel },
        500: { "description": "failed to fetch after update", "model": DetailModel },
    },
    operation_id="update_officer_info"
)
async def update_info(
    request: Request,
    db_session: database.DBSession,
    computing_id: str,
    officer_info_upload: OfficerUpdate | OfficerSelfUpdate
):
    is_site_admin, _, session_computing_id = await is_website_admin(request, db_session)

    if computing_id != session_computing_id and not is_site_admin:
        raise HTTPException(status_code=403, detail="you may not update other officers")

    old_officer_info = await officers.crud.get_officer_info_or_raise(db_session, computing_id)
    old_officer_info.update_from_params(officer_info_upload)
    await officers.crud.update_officer_info(db_session, old_officer_info)

    # TODO (#27): log all important changes just to a .log file & persist them for a few years

    await db_session.commit()

    updated_officer_info = await officers.crud.get_new_officer_info_or_raise(db_session, computing_id)
    return JSONResponse(updated_officer_info)

@router.patch(
    "/term/{term_id:int}",
    description="Update the information for an Officer's term",
    response_model=OfficerTermResponse,
    responses={
        403: { "description": "must be a website admin", "model": DetailModel },
        500: { "description": "failed to fetch after update", "model": DetailModel },
    },
    operation_id="update_officer_term_by_id"
)
async def update_term(
    request: Request,
    db_session: database.DBSession,
    term_id: int,
    body: OfficerTermUpdate
):
    """
    A website admin may change the position & term length however they wish.
    """
    is_site_admin, _, session_computing_id = await is_website_admin(request, db_session)

    old_officer_term = await officers.crud.get_officer_term_by_id_or_raise(db_session, term_id)
    if not is_site_admin:
        if old_officer_term.computing_id != session_computing_id:
            raise HTTPException(status_code=403, detail="you may not update other officer terms")

        if utils.is_past_term(old_officer_term):
            raise HTTPException(status_code=403, detail="you may not update past terms")

    old_officer_term.update_from_params(body)

    # TODO (#27): log all important changes to a .log file
    await officers.crud.update_officer_term(db_session, old_officer_term)

    await db_session.commit()

    new_officer_term = await officers.crud.get_officer_term_by_id_or_raise(db_session, term_id)
    return JSONResponse(new_officer_term)

@router.delete(
    "/term/{term_id:int}",
    description="Remove the specified officer term. Only website admins can run this endpoint. BE CAREFUL WITH THIS!",
    response_model=SuccessResponse,
    responses={
        401: { "description": "must be logged in", "model": DetailModel },
        403: { "description": "must be a website admin", "model": DetailModel },
        500: { "description": "server error", "model": DetailModel },
    },
    operation_id="delete_officer_term_by_id"
)
async def remove_officer_term(
    request: Request,
    db_session: database.DBSession,
    term_id: int,
):
    await admin_or_raise(request, db_session)

    # TODO (#27): log all important changes to a .log file

    await officers.crud.delete_officer_term_by_id(db_session, term_id)
    await db_session.commit()

    return SuccessResponse(success=True)
