from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

import auth.crud
import database
import officers.crud
import utils
from dependencies import LoggedInUser, SessionUser, perm_admin
from officers.constants import OfficerPositionEnum
from officers.models import (
    OfficerCreate,
    OfficerInfo,
    OfficerPrivate,
    OfficerPublic,
    OfficerTerm,
    OfficerTermUpdate,
    OfficerUpdate,
)
from permission.types import OfficerPrivateInfo
from utils.permissions import is_user_website_admin, verify_update
from utils.shared_models import DetailModel, SuccessResponse

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

# ---------------------------------------- #
# checks


async def _has_officer_private_info_access(
    request: Request, db_session: database.DBSession
) -> tuple[
    bool,
    str | None,
]:
    """determine if the user has access to private officer info"""
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        return False, None

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if computing_id is None:
        return False, None

    # TODO: Fix this permission
    has_private_access = await OfficerPrivateInfo.has_permission(db_session, computing_id)
    return has_private_access, computing_id


# ---------------------------------------- #
# endpoints


@router.get(
    "/current",
    description="Get information about the current officers. With no authorization, only get basic info.",
    response_model=dict[OfficerPositionEnum, OfficerPublic],
    operation_id="get_current_officers",
)
async def current_officers(
    request: Request,
    db_session: database.DBSession,
):
    has_private_access, _ = await _has_officer_private_info_access(request, db_session)

    curr_officers = await officers.crud.current_officers(db_session, has_private_access)

    res = {}
    for officer in curr_officers:
        res[officer.position] = officer.model_dump(mode="json")

    return JSONResponse(res)


@router.get(
    "/all",
    description="Information for all execs from all exec terms",
    response_model=list[OfficerPrivate] | list[OfficerPublic],
    responses={403: {"description": "not authorized", "model": DetailModel}},
    operation_id="get_all_officers",
)
async def all_officers(
    request: Request,
    db_session: database.DBSession,
    # Officer terms for officers which have not yet started their term yet are considered private,
    # and may only be accessed by that officer and executives. All other officer terms are public.
    include_future_terms: bool = False,
):
    has_private_access, computing_id = await _has_officer_private_info_access(request, db_session)
    if include_future_terms and (computing_id is None or not (await is_user_website_admin(computing_id, db_session))):
        raise HTTPException(status_code=401, detail="not authorized")

    all_officers = await officers.crud.get_all_officers(db_session, include_future_terms, has_private_access)

    return JSONResponse([officer_data.model_dump(mode="json") for officer_data in all_officers])


@router.get(
    "/terms/{computing_id}",
    description="""
        Get term info for an executive. All term info is public for all past or active terms.
        Future terms can only be accessed by website admins.
    """,
    response_model=list[OfficerTerm],
    responses={
        401: {"description": "not logged in", "model": DetailModel},
        403: {"description": "not authorized to view private info", "model": DetailModel},
    },
    operation_id="get_officer_terms_by_id",
)
async def get_officer_terms(
    user_id: SessionUser, db_session: database.DBSession, computing_id: str, include_future_terms: bool = False
):
    if include_future_terms:
        await verify_update(user_id, db_session, computing_id)

    # all term info is public, so anyone can get any of it
    officer_terms = await officers.crud.get_officer_terms(db_session, computing_id, include_future_terms)
    return JSONResponse([OfficerTerm.model_validate(term).model_dump(mode="json") for term in officer_terms])


@router.get(
    "/info/{computing_id}",
    description="Get officer info for the current user, if they've ever been an exec. Only admins can get info about another user.",
    response_model=OfficerInfo,
    responses={403: {"description": "not authorized to view author user info", "model": DetailModel}},
    operation_id="get_officer_info_by_id",
)
async def get_officer_info(
    db_session: database.DBSession,
    session_computing_id: LoggedInUser,
    computing_id: str,
):
    if computing_id != session_computing_id and not await is_user_website_admin(session_computing_id, db_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized")

    officer_info = await officers.crud.get_officer_info_or_raise(db_session, computing_id)
    return JSONResponse(officer_info.serializable_dict())


@router.post(
    "/term",
    description="""
        Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA.
        Updates the system with a new officer, and enables the user to login to the system to input their information.
    """,
    response_model=list[OfficerTerm],
    responses={
        403: {"description": "must be a website admin", "model": DetailModel},
        500: {"model": DetailModel},
    },
    operation_id="create_officer_term",
    dependencies=[Depends(perm_admin)],
)
async def create_officer_term(
    db_session: database.DBSession,
    officer_list: list[OfficerCreate],
):
    new_terms = await officers.crud.create_multiple_officers(db_session, officer_list)
    content = [term.serializable_dict() for term in new_terms]

    await db_session.commit()
    return JSONResponse(content)


@router.patch(
    "/info/{computing_id}",
    description="""
        After election, officer computing ids are input into our system.
        If you have been elected as a new officer, you may authenticate with SFU CAS,
        then input your information & the valid token for us. Admins may update this info.
    """,
    response_model=OfficerInfo,
    responses={
        403: {"description": "must be a website admin", "model": DetailModel},
        500: {"description": "failed to fetch after update", "model": DetailModel},
    },
    operation_id="update_officer_info",
)
async def update_officer_info(
    user_id: SessionUser,
    db_session: database.DBSession,
    computing_id: str,
    officer_info_upload: OfficerUpdate,
):
    await verify_update(user_id, db_session, computing_id)

    old_officer_info = await officers.crud.get_officer_info_or_raise(db_session, computing_id)
    old_officer_info.update_from_params(officer_info_upload)
    await officers.crud.update_officer_info(db_session, old_officer_info)

    # TODO (#27): log all important changes just to a .log file & persist them for a few years

    await db_session.commit()

    updated_officer_info = await officers.crud.get_new_officer_info_or_raise(db_session, computing_id)
    return JSONResponse(updated_officer_info.serializable_dict())


@router.patch(
    "/term/{term_id}",
    description="Update the information for an Officer's term",
    response_model=OfficerTerm,
    responses={
        403: {"description": "must be a website admin", "model": DetailModel},
        500: {"description": "failed to fetch after update", "model": DetailModel},
    },
    operation_id="update_officer_term_by_id",
    dependencies=[Depends(perm_admin)],
)
async def update_officer_term(db_session: database.DBSession, term_id: int, body: OfficerTermUpdate):
    """
    A website admin may change the position & term length however they wish.
    For now, only website admins can change these things.
    """

    old_officer_term = await officers.crud.get_officer_term_by_id_or_raise(db_session, term_id)

    # TODO: Enable this check if we allow non-website admins to change their information
    # if utils.is_past_term(old_officer_term):
    #     raise HTTPException(status_code=403, detail="you may not update past terms")

    new_data = body.model_dump(exclude_unset=True)

    for key, value in new_data.items():
        setattr(old_officer_term, key, value)

    # TODO (#27): log all important changes to a .log file
    await officers.crud.update_officer_term(db_session, old_officer_term)

    await db_session.commit()
    await db_session.refresh(old_officer_term)

    return JSONResponse(OfficerTerm.model_validate(old_officer_term).model_dump(mode="json"))


@router.delete(
    "/term/{term_id}",
    description="Remove the specified officer term. Only website admins can run this endpoint. BE CAREFUL WITH THIS!",
    response_model=SuccessResponse,
    responses={
        401: {"description": "must be logged in", "model": DetailModel},
        403: {"description": "must be a website admin", "model": DetailModel},
        500: {"description": "server error", "model": DetailModel},
    },
    operation_id="delete_officer_term_by_id",
    dependencies=[Depends(perm_admin)],
)
async def delete_officer_term(
    db_session: database.DBSession,
    term_id: int,
):
    # TODO (#27): log all important changes to a .log file
    # TODO: Double check that the delete was successful
    await officers.crud.delete_officer_term_by_id(db_session, term_id)
    await db_session.commit()

    return SuccessResponse(success=True)
