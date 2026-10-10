from datetime import datetime, timedelta

from asyncpg import UniqueViolationError
from asyncpg.exceptions import CheckViolationError, ExclusionViolationError, ForeignKeyViolationError
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

import database
import officers.crud
from auth.constants import UserRole
from auth.crud import SessionUser
from constants import TZ_INFO
from dependencies import AuthenticatedUser, OptionalSessionUser, perm_admin, perm_exec
from officers.models import (
    OfficerCreate,
    OfficerPosition,
    OfficerPositionCreate,
    OfficerPositionUpdate,
    OfficerPositionVersionCreate,
    OfficerUpdate,
    PrivateOfficerTerm,
    PublicOfficerTerm,
)
from officers.tables import OfficerInfoDB, OfficerPositionDB, OfficerPositionVersionDB, OfficerTermDB
from utils.permissions import has_role
from utils.shared_models import DetailModel

router = APIRouter(
    prefix="/officer",
    tags=["officer"],
)

# ---------------------------------------- #
# checks


async def get_officer_term_or_raise(db_session: database.DBSession, term_id: int) -> OfficerTermDB:
    officer_term = await officers.crud.get_officer_term_by_id(db_session, term_id)
    if officer_term is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer term not found")
    return officer_term


# ---------------------------------------- #
# endpoints


@router.get(
    "",
    description="Get all officer terms",
    response_model=list[PublicOfficerTerm],
    responses={
        403: {"description": "Not authorized", "model": DetailModel},
    },
    operation_id="get_all_officers",
)
async def all_officers(
    db_session: database.DBSession,
    session_user: OptionalSessionUser,
    current: bool = Query(False, description="Only fetch the officer terms that are currently active"),
):
    if current:
        officer_list = await officers.crud.get_active_officer_terms(db_session)
    else:
        officer_list = await officers.crud.get_officer_terms(
            db_session,
            include_future_terms=has_role(session_user, UserRole.ADMIN),
        )

    return JSONResponse(
        [PublicOfficerTerm.from_db(officer_data).model_dump(mode="json") for officer_data in officer_list]
    )


@router.get(
    "/private",
    description="Get all officer terms, with private data.",
    response_model=list[PrivateOfficerTerm],
    responses={
        403: {"description": "Not authorized", "model": DetailModel},
    },
    operation_id="get_all_officers_private",
    dependencies=[Depends(perm_exec)],
)
async def admin_get_all_officers(
    db_session: database.DBSession,
    session_user: OptionalSessionUser,
    current: bool = Query(False, description="Only fetch the officer terms that are currently active"),
):
    if current:
        officer_list = await officers.crud.get_active_officer_terms(db_session)
    else:
        officer_list = await officers.crud.get_officer_terms(
            db_session,
            include_future_terms=True,
        )

    return JSONResponse(
        [PrivateOfficerTerm.from_db(officer_data).model_dump(mode="json") for officer_data in officer_list]
    )


@router.post(
    "",
    description="Only the SysAdmin, President, or Secretary can submit this request. It will usually be the Secretary."
    "Updates the system with a new officer, and enables the user to login to the system to input their information. ",
    response_model=list[PrivateOfficerTerm],
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
    content = [PrivateOfficerTerm.from_db(term).model_dump(mode="json") for term in new_terms]

    await db_session.commit()
    return content


@router.patch(
    "/term/{term_id}",
    description="Update the information for an Officer's term",
    response_model=PrivateOfficerTerm,
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
        404: {"description": "Officer term not found", "model": DetailModel},
    },
    operation_id="update_officer_term_by_id",
    dependencies=[Depends(perm_admin)],
)
async def update_officer_term(db_session: database.DBSession, term_id: int, body: OfficerUpdate):
    """
    A website admin may change the position & term length however they wish.
    For now, only website admins can change these things.
    """

    officer_term = await get_officer_term_or_raise(db_session, term_id)

    if body.info is None and body.term is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="No fields to update")

    if body.info is not None:
        for key, value in body.info.model_dump(exclude_unset=True).items():
            setattr(officer_term.officer, key, value)

    if body.term is not None:
        for key, value in body.term.model_dump(exclude_unset=True).items():
            setattr(officer_term, key, value)

    await db_session.flush()
    response = PrivateOfficerTerm.from_db(officer_term)
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


@router.get(
    "/position",
    description="Returns officer positions and their latest version",
    response_model=list[OfficerPosition],
    operation_id="get_officer_positions",
)
async def get_officer_positions(
    db_session: database.DBSession,
    active: bool = Query(False, description="If true, only return positions that are currently active."),
):
    positions = await officers.crud.get_officer_positions(db_session, active)
    return [OfficerPosition.from_db(pos) for pos in positions]


@router.post(
    "/position",
    description="Create a brand new officer position. The role must not already exist in the system.",
    response_model=OfficerPosition,
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
        409: {"description": "Position already exists", "model": DetailModel},
    },
    operation_id="create_officer_position",
    dependencies=[Depends(perm_admin)],
)
async def create_officer_position(db_session: database.DBSession, body: OfficerPositionCreate):
    position = OfficerPositionDB(position=body.name)
    db_session.add(position)

    try:
        await db_session.flush()
    except IntegrityError as e:
        await db_session.rollback()
        code = getattr(e.orig, "sqlstate", None)
        if code != UniqueViolationError.sqlstate:
            raise

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Officer position already exists") from e

    # If this is a brand new officer position we need to create a version too
    version = OfficerPositionVersionDB(
        position_id=position.id,
        type=body.type,
        multiple_allowed=body.multiple_allowed,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
    )
    db_session.add(version)

    try:
        await db_session.flush()
    except IntegrityError as e:
        await db_session.rollback()
        code = getattr(e.orig, "sqlstate", None)
        if code != ForeignKeyViolationError.sqlstate:
            raise

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Officer position failed to be made") from e

    response = OfficerPosition.from_pos_and_ver(position, version)
    await db_session.commit()
    return response


@router.post(
    "/position/{position_id}",
    description="Creates a new version of the position and updates the effective date of the previous version. Use this to modify an active position or create a new version of an existing position",
    response_model=OfficerPosition,
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
        400: {"description": "New version is incompatible", "model": DetailModel},
        404: {"description": "Position doesn't exist", "model": DetailModel},
    },
    operation_id="create_officer_position_version",
    dependencies=[Depends(perm_admin)],
)
async def create_officer_position_version(
    db_session: database.DBSession, position_id: int, body: OfficerPositionVersionCreate
):
    old_version = await officers.crud.get_latest_officer_position_version(db_session, position_id)

    if not old_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer position doesn't exist")

    if old_version.effective_from >= body.effective_from or (
        old_version.effective_to is not None and old_version.effective_to >= body.effective_from
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New version must start after the old one")

    new_version = OfficerPositionVersionDB(
        position_id=old_version.position_id,
        type=body.type,
        multiple_allowed=body.multiple_allowed,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
    )

    # Only update the effective to date if it is an active position
    if old_version.effective_to is None:
        old_version.effective_to = body.effective_from - timedelta(days=1)

    db_session.add(new_version)

    try:
        await db_session.flush()
        new_position_version = OfficerPosition.from_db(new_version)
        await db_session.commit()
        return new_position_version
    except IntegrityError as e:
        await db_session.rollback()
        code = getattr(e.orig, "sqlstate", None)
        if code == ForeignKeyViolationError.sqlstate:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Officer position doesn't exist") from e
        if code == CheckViolationError.sqlstate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New version is incompatible") from e
        raise


@router.patch(
    "/position/{position_id}",
    description="Updates a position version. Only use this on an active position.",
    response_model=OfficerPosition,
    responses={
        401: {"description": "Must be logged in", "model": DetailModel},
        403: {"description": "Must be an admin", "model": DetailModel},
        400: {"description": "New version is incompatible", "model": DetailModel},
        404: {"description": "Position doesn't exist", "model": DetailModel},
        409: {"description": "New version overlaps with an existing version", "model": DetailModel},
    },
    operation_id="mark_position_inactive",
    dependencies=[Depends(perm_admin)],
)
async def update_officer_position_version(
    db_session: database.DBSession, position_id: int, body: OfficerPositionUpdate
):
    version = await officers.crud.get_active_officer_position_version(db_session, position_id)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Officer position doesn't exist or is inactive"
        )

    if body.effective_to and body.effective_to <= version.effective_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Effective to date must be after the effective from date",
        )

    version.effective_to = body.effective_to

    try:
        await db_session.flush()
        response = OfficerPosition.from_db(version)
        await db_session.commit()
        return response
    except IntegrityError as e:
        await db_session.rollback()
        code = getattr(e.orig, "sqlstate", None)
        if code == CheckViolationError.sqlstate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New version is incompatible",
            ) from e
        if code == ExclusionViolationError.sqlstate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New version overlaps with an existing version",
            ) from e
        raise
