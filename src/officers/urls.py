from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

import database
import officers.crud
from auth.constants import UserRole
from auth.crud import SessionUser
from dependencies import AuthenticatedUser, OptionalSessionUser, perm_admin
from officers.models import (
    Officer,
    OfficerCreate,
    OfficerInfo,
    OfficerInfoUpdate,
    OfficerTerm,
    OfficerTermUpdate,
)
from officers.tables import OfficerInfoDB, OfficerTermDB
from utils.permissions import has_role
from utils.shared_models import DetailModel

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

# ---------------------------------------- #
# checks


def verify_update(user_id: SessionUser, computing_id: str):
    if user_id.computing_id != computing_id and not has_role(user_id, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )


async def get_officer_info_or_raise(db_session: database.DBSession, computing_id: str) -> OfficerInfoDB:
    officer_info = await officers.crud.get_officer_info(db_session, computing_id)
    if officer_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer info not found")
    return officer_info


async def get_officer_term_or_raise(db_session: database.DBSession, term_id: int) -> OfficerTermDB:
    officer_term = await officers.crud.get_officer_term_by_id(db_session, term_id)
    if officer_term is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer term not found")
    return officer_term


# ---------------------------------------- #
# endpoints


@router.get(
    "/current",
    description="Get information about the current officers. With no authorization, only get basic info.",
    response_model=list[Officer],
    operation_id="get_current_officers",
)
async def current_officers(db_session: database.DBSession, session_user: OptionalSessionUser):
    has_private_access = has_role(session_user, UserRole.EXEC)

    curr_officers = await officers.crud.current_officers(db_session, has_private_access)

    return JSONResponse([o.model_dump(mode="json", exclude_unset=True) for o in curr_officers])


@router.get(
    "/all",
    description="Information for all execs from all exec terms",
    response_model=list[Officer],
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Not authorized", "model": DetailModel},
    },
    operation_id="get_all_officers",
)
async def all_officers(
    db_session: database.DBSession,
    session_user: OptionalSessionUser,
    # Officer terms for officers which have not yet started their term yet are considered private,
    # and may only be accessed by admins.
    include_future_terms: bool = False,
):
    is_admin = has_role(session_user, UserRole.ADMIN)
    has_private_access = is_admin or has_role(session_user, UserRole.EXEC)

    if include_future_terms and not is_admin:
        status_code = status.HTTP_401_UNAUTHORIZED if session_user is None else status.HTTP_403_FORBIDDEN
        raise HTTPException(status_code=status_code, detail="Not authorized")

    all_officers = await officers.crud.get_all_officers(db_session, include_future_terms, has_private_access)

    return JSONResponse([officer_data.model_dump(mode="json", exclude_unset=True) for officer_data in all_officers])


@router.get(
    "/terms/{computing_id}",
    description="""
        Get term info for an executive. All term info is public for all past or active terms.
        Future terms can only be accessed by website admins.
    """,
    response_model=list[OfficerTerm],
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Not authorized to view private information", "model": DetailModel},
    },
    operation_id="get_officer_terms_by_id",
)
async def get_officer_terms(
    session_user: OptionalSessionUser,
    db_session: database.DBSession,
    computing_id: str,
    include_future_terms: bool = False,
):
    if include_future_terms:
        if not has_role(session_user, UserRole.ADMIN):
            status_code = status.HTTP_401_UNAUTHORIZED if session_user is None else status.HTTP_403_FORBIDDEN
            raise HTTPException(status_code=status_code, detail="Not authorized")

    # all term info is public, so anyone can get any of it
    officer_terms = await officers.crud.get_officer_terms(db_session, computing_id, include_future_terms)
    return JSONResponse(
        [OfficerTerm.model_validate(term).model_dump(mode="json", exclude_unset=True) for term in officer_terms]
    )


@router.get(
    "/info/{computing_id}",
    description="Get officer info for the current user, if they've ever been an exec. Only admins can get info about another user.",
    response_model=OfficerInfo,
    responses={403: {"description": "Must be an admin", "model": DetailModel}},
    operation_id="get_officer_info_by_id",
)
async def get_officer_info(
    db_session: database.DBSession,
    session_user: AuthenticatedUser,
    computing_id: str,
):
    verify_update(session_user, computing_id)

    officer_info = await get_officer_info_or_raise(db_session, computing_id)
    return JSONResponse(OfficerInfo.model_validate(officer_info).model_dump(mode="json", exclude_unset=True))


@router.post(
    "/term",
    description="Only the SysAdmin, President, or Secretary can submit this request. It will usually be the Secretary. Updates the system with a new officer, and enables the user to login to the system to input their information. ",
    response_model=list[OfficerTerm],
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
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
    content = [OfficerTerm.model_validate(term).model_dump(mode="json", exclude_unset=True) for term in new_terms]

    await db_session.commit()
    return JSONResponse(content)


@router.patch(
    "/info/{computing_id}",
    description="Updates an officer's info.",
    response_model=OfficerInfo,
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
        404: {"description": "Officer info not found", "model": DetailModel},
    },
    operation_id="update_officer_info",
    dependencies=[Depends(perm_admin)],
)
async def update_officer_info(
    db_session: database.DBSession,
    computing_id: str,
    body: OfficerInfoUpdate,
):
    # TODO: Enable this when officers are allowed to self update
    # verify_update(session_user, computing_id)

    officer_info = await get_officer_info_or_raise(db_session, computing_id)

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(officer_info, k, v)

    await db_session.flush()

    response = OfficerInfo.model_validate(officer_info)

    await db_session.commit()
    return response


@router.patch(
    "/term/{term_id}",
    description="Update the information for an Officer's term",
    response_model=OfficerTerm,
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
        404: {"description": "Officer term not found", "model": DetailModel},
    },
    operation_id="update_officer_term_by_id",
    dependencies=[Depends(perm_admin)],
)
async def update_officer_term(db_session: database.DBSession, term_id: int, body: OfficerTermUpdate):
    """
    A website admin may change the position & term length however they wish.
    For now, only website admins can change these things.
    """

    officer_term = await get_officer_term_or_raise(db_session, term_id)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(officer_term, key, value)

    await db_session.flush()

    await db_session.refresh(officer_term)
    response = OfficerTerm.model_validate(officer_term)

    await db_session.commit()
    return response


@router.delete(
    "/term/{term_id}",
    description="Remove the specified officer term. Only website admins can run this endpoint. BE CAREFUL WITH THIS!",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
    },
    operation_id="delete_officer_term_by_id",
    dependencies=[Depends(perm_admin)],
)
async def delete_officer_term(
    db_session: database.DBSession,
    term_id: int,
):
    await officers.crud.delete_officer_term_by_id(db_session, term_id)
    await db_session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
