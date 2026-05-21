from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

import database
import event.crud
from dependencies import perm_admin
from event.models import (
    Event,
    EventCreate,
    EventUpdate,
    EventDelete
)
from event.tables import EventDB
from utils.shared_models import DetailModel, SuccessResponse
from datetime import datetime, date
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder

router = APIRouter(
    prefix="/event",
    tags=["event"],
)

@router.get(
    "",
    description="Get all events",
    response_model=list[Event],
    operation_id="get_all_events",
)
async def get_all_events(
    db_session: database.DBSession,
):
    events_list = await event.crud.get_all_events(db_session)

    return events_list


@router.get(
    "/{year}",
    description="Get events that start OR end in this year",
    response_model=list[Event],
    operation_id="get_events_for_this_year"
)
async def get_events_for_this_year(
    db_session: database.DBSession,
    year: int,
):
    events_list = await event.crud.get_events_for_this_year(db_session, year)

    return events_list


@router.get(
    "/{year}/{month}",
    description="Get events that start OR end in the given year and month",
    response_model=list[Event],
    operation_id="get_events_for_this_year_month"
)
async def get_events_for_this_year_month(
    db_session: database.DBSession,
    year: int,
    month: int
):
    events_list = await event.crud.get_events_for_this_year_month(db_session, year, month)

    return events_list


@router.post(
    "",
    description="Create a new event",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    responses={
        500: {"description": "failed to fetch new event", "model": DetailModel},
    },
    operation_id="create_event",
    dependencies=[Depends(perm_admin)],
)
async def create_event(
    db_session: database.DBSession,
    body: EventCreate
):
    new_event = EventDB(**body.model_dump())
    await event.crud.create_event(
        db_session,
        new_event,
    )

    await db_session.commit()
    await db_session.refresh(new_event)

    return new_event


@router.patch(
    "/{eid}",
    description="Update an Event detail",
    response_model=Event,
    responses={
        404:{"description": "Event doesn't exist."}
    },
    operation_id="update_event",
    dependencies=[Depends(perm_admin)],
)
async def update_event(
    db_session: database.DBSession,
    eid: int,
    body: EventUpdate
):
    db_event = await event.crud.get_event_by_eid(db_session, eid)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event doesn't exist."
        )

    db_data = Event.model_validate(db_event).model_dump()
    patch_data = body.model_dump(exclude_unset=True)

    merged_data = { **db_data, **patch_data}
    try:
        Event.model_validate(merged_data)
    except ValidationError as e:
        raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=jsonable_encoder(e.errors())
            )

    for key, value in patch_data.items():
        setattr(db_event, key, value)
    
    await db_session.commit()
    await db_session.refresh(db_event)

    return db_event



@router.delete(
    "/{eid}",
    description="Delete an event",
    response_model=EventDelete,
    responses={
        404:{"description": "Event doesn't exist."}
    },
    operation_id="delete_event",
    dependencies=[Depends(perm_admin)],
)
async def delete_event(
    db_session: database.DBSession,
    eid: int
):
    rows_deleted = await event.crud.delete_event(db_session, eid)

    if rows_deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event doesn't exist."
        )

    await db_session.commit()
    return EventDelete(result=True, eid=eid)