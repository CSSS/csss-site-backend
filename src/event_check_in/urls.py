from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

import database
import event.crud
import event_check_in.crud
from constants import INT64_MAX
from dependencies import perm_event, perm_exec
from event_check_in.models import EventCheckIn, EventCheckInCreate, EventCheckInUpdate
from event_check_in.tables import EventCheckInDB
from utils.shared_models import DetailModel

CheckInIdPath = Annotated[int, Path(ge=1, le=INT64_MAX)]

router = APIRouter(
    prefix="/event/{eid}/check-in",
    tags=["event check-in"],
    responses={
        401: {"model": DetailModel, "description": "Not authenticated"},
        403: {"model": DetailModel, "description": "Not authorized"},
        404: {"model": DetailModel, "description": "Event or check-in configuration not found"},
    },
)


async def _get_event_id(db_session: database.DBSession, eid: str) -> int:
    # Convert the public event ID from the URL into the database's internal ID
    db_event = await event.crud.get_event_by_eid(db_session, eid)
    if db_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return db_event.id


async def _save_check_in(
    db_session: database.DBSession,
    check_in: EventCheckInDB,
) -> EventCheckIn:
    try:
        # Write pending changes and load database-generated IDs and timestamps
        await db_session.flush()
        await db_session.refresh(check_in)

        # Copy values into the response model before commit expires in the database object
        response = EventCheckIn.model_validate(check_in)
        await db_session.commit()
    except IntegrityError as error:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to save check-in configuration.",
        ) from error
    return response


@router.get(
    "",
    operation_id="get_check_ins",
    response_model=list[EventCheckIn],
    dependencies=[Depends(perm_exec)],
)
async def list_check_ins(db_session: database.DBSession, eid: str):
    event_id = await _get_event_id(db_session, eid)
    return await event_check_in.crud.get_check_ins(db_session, event_id)


@router.get(
    "/{check_in_id}",
    operation_id="get_check_in",
    response_model=EventCheckIn,
    dependencies=[Depends(perm_exec)],
)
async def get_check_in(
    db_session: database.DBSession,
    eid: str,
    check_in_id: CheckInIdPath,
):
    check_in = await event_check_in.crud.get_check_in(db_session, eid, check_in_id)
    if check_in is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event or event check-in configuration is missing",
        )
    return check_in


@router.post(
    "",
    operation_id="create_check_in",
    response_model=EventCheckIn,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": DetailModel, "description": "Database conflict"}},
    dependencies=[Depends(perm_event)],
)
async def create_check_in(
    db_session: database.DBSession,
    eid: str,
    body: EventCheckInCreate,
):
    event_id = await _get_event_id(db_session, eid)
    check_in = event_check_in.crud.create_check_in(db_session, event_id, body)
    return await _save_check_in(db_session, check_in)


@router.patch(
    "/{check_in_id}",
    operation_id="update_check_in",
    response_model=EventCheckIn,
    responses={409: {"model": DetailModel, "description": "Database conflict"}},
    dependencies=[Depends(perm_event)],
)
async def update_check_in(
    db_session: database.DBSession,
    eid: str,
    check_in_id: CheckInIdPath,
    body: EventCheckInUpdate,
):
    check_in = await event_check_in.crud.get_check_in(db_session, eid, check_in_id, for_update=True)
    if check_in is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event or event check-in configuration is missing",
        )

    current = EventCheckInCreate.model_validate(check_in, from_attributes=True)

    # Apply only supplied fields; explicit nulls can clear the optional time limits
    updated_data = current.model_dump() | body.model_dump(exclude_unset=True)

    try:
        # Check the complete time range, including any unchanged opening or closing time
        validated = EventCheckInCreate.model_validate(updated_data)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=jsonable_encoder(error.errors(include_context=False)),
        ) from error

    event_check_in.crud.update_check_in(check_in, validated)
    return await _save_check_in(db_session, check_in)


@router.delete(
    "/{check_in_id}",
    operation_id="delete_check_in",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(perm_event)],
)
async def delete_check_in(
    db_session: database.DBSession,
    eid: str,
    check_in_id: CheckInIdPath,
):
    event_id = await _get_event_id(db_session, eid)

    # For an existing event, deletion succeeds even if the configuration is already absent
    await event_check_in.crud.delete_check_in(db_session, event_id, check_in_id)
    await db_session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
