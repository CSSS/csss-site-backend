from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

import auth.crud
import database
import officers.crud
import utils
from officers.models import PrivateOfficerResponse, PublicOfficerResponse
from officers.tables import OfficerInfo, OfficerTerm
from officers.types import InitialOfficerInfo, OfficerInfoUpload, OfficerTermUpload
from permission.types import OfficerPrivateInfo, WebsiteAdmin
from utils.shared_models import DetailModel
from utils.urls import logged_in_or_raise

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
    response_model=list[PrivateOfficerResponse] | list[PublicOfficerResponse],
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
    response_model=list[PrivateOfficerResponse] | list[PublicOfficerResponse],
    responses={
        401: { "description": "not authorized to view private info", "model": DetailModel }
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

    all_officers = await officers.crud.all_officers(db_session, has_private_access, include_future_terms)
    if has_private_access:
        return JSONResponse([
            PrivateOfficerResponse.model_validate(officer_data)
            for officer_data in all_officers
        ])
    else:
        return JSONResponse([
            PublicOfficerResponse.model_validate(officer_data)
            for officer_data in all_officers
        ])

@router.get(
    "/terms/{computing_id}",
    description="""
        Get term info for an executive. All term info is public for all past or active terms.
        Future terms can only be accessed by website admins.
    """,
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

    officer_info = await officers.crud.get_officer_info_or_raise(db_session, computing_id)
    return JSONResponse(officer_info.serializable_dict())

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

    _, session_computing_id = await logged_in_or_raise(request, db_session)
    await WebsiteAdmin.has_permission_or_raise(db_session, session_computing_id)

    for officer_info in officer_info_list:
        # if user with officer_info.computing_id has never logged into the website before,
        # a site_user tuple will be created for them.
        await officers.crud.create_new_officer_info(db_session, OfficerInfo(
            computing_id = officer_info.computing_id,
            # TODO (#71): use sfu api to get legal name from officer_info.computing_id
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
            start_date = officer_info.start_date,
        ))

    await db_session.commit()
    return PlainTextResponse("ok")

@router.patch(
    "/info/{computing_id}",
    description="""
        After election, officer computing ids are input into our system.
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
    _, session_computing_id = await logged_in_or_raise(request, db_session)

    if computing_id != session_computing_id:
        await WebsiteAdmin.has_permission_or_raise(
            db_session, session_computing_id,
            errmsg="must have website admin permissions to update another user"
        )

    old_officer_info = await officers.crud.get_officer_info_or_raise(db_session, computing_id)
    validation_failures, corrected_officer_info = await officer_info_upload.validate(computing_id, old_officer_info)

    # TODO (#27): log all important changes just to a .log file & persist them for a few years

    success = await officers.crud.update_officer_info(db_session, corrected_officer_info)
    if not success:
        raise HTTPException(status_code=400, detail="officer_info does not exist yet, please create the officer info entry first")

    await db_session.commit()

    updated_officer_info = await officers.crud.get_officer_info_or_raise(db_session, computing_id)
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
    """
    A website admin may change the position & term length however they wish.
    """
    officer_term_upload.valid_or_raise()
    _, session_computing_id = await logged_in_or_raise(request, db_session)

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
        officer_term_upload.computing_id != old_officer_term.computing_id
        or officer_term_upload.position != old_officer_term.position
        or officer_term_upload.start_date != old_officer_term.start_date
        or officer_term_upload.end_date != old_officer_term.end_date
    ):
        await WebsiteAdmin.has_permission_or_raise(
            db_session, session_computing_id,
            errmsg="only admins can write new versions of position, start_date, and end_date"
        )

    # TODO (#27): log all important changes to a .log file
    success = await officers.crud.update_officer_term(
        db_session,
        officer_term_upload.to_officer_term(term_id)
    )
    if not success:
        raise HTTPException(status_code=400, detail="the associated officer_term does not exist yet, please create it first")

    await db_session.commit()

    new_officer_term = await officers.crud.get_officer_term_by_id(db_session, term_id)
    return JSONResponse({
        "officer_term": new_officer_term.serializable_dict(),
        # none for now, but may be added if frontend requests
        "validation_failures": [],
    })

@router.delete(
    "/term/{term_id}",
    description="Remove the specified officer term. Only website admins can run this endpoint. BE CAREFUL WITH THIS!",
)
async def remove_officer(
    request: Request,
    db_session: database.DBSession,
    term_id: int,
):
    _, session_computing_id = await logged_in_or_raise(request, db_session)
    await WebsiteAdmin.has_permission_or_raise(
        db_session, session_computing_id,
        errmsg="must have website admin permissions to remove a term"
    )

    deleted_officer_term = await officers.crud.get_officer_term_by_id(db_session, term_id)

    # TODO (#27): log all important changes to a .log file

    # TODO (#100): return whether the deletion succeeded or not
    await officers.crud.delete_officer_term_by_id(db_session, term_id)
    await db_session.commit()

    return JSONResponse({
        "officer_term": deleted_officer_term.serializable_dict(),
    })
