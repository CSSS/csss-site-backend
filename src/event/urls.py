import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError

import database
import event.crud
from dependencies import MonthPath, YearPath, perm_admin
from event.models import Event, EventCreate, EventDelete, EventUpdate, GroupEvent, GroupEventDeleteResponse
from event.tables import EventDB
from utils.shared_models import DetailModel

router = APIRouter(
    prefix="/event",
    tags=["event"],
)


class GetQueryParams(BaseModel):
    include_cancelled: bool = Field(False, description="Include cancelled events in the response.")
    current: bool = Field(False, description="Only get events that haven't ended yet.")


@router.get(
    "",
    description="Get all events",
    response_model=list[Event],
    operation_id="get_all_events",
)
async def get_all_events(db_session: database.DBSession, q: Annotated[GetQueryParams, Query()]):
    if q.current:
        events_list = await event.crud.get_upcoming_events(db_session, q.include_cancelled)
    else:
        events_list = await event.crud.get_all_events(db_session, q.include_cancelled)

    return events_list


@router.get(
    "/{year}/{month}",
    description="Get events that overlap in the year and month.",
    response_model=list[Event],
    operation_id="get_events_for_this_year_month",
)
async def get_events_for_this_year_month(
    db_session: database.DBSession, year: YearPath, month: MonthPath, include_cancelled: bool = False
):
    events_list = await event.crud.get_events_for_this_year_month(db_session, year, month, include_cancelled)

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
async def create_event(db_session: database.DBSession, body: EventCreate):
    new_event = EventDB(**body.model_dump())
    event.crud.create_event(
        db_session,
        new_event,
    )

    await db_session.commit()
    await db_session.refresh(new_event)

    return new_event


@router.post(
    "/group",
    description="Creates one or more events under the same group key.",
    response_model=GroupEvent,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_group_event",
    dependencies=[Depends(perm_admin)],
)
async def create_group_events(db_session: database.DBSession, body: Annotated[list[EventCreate], Body(min_length=1)]):
    g_id = uuid.uuid4()
    # Create new EventDBs by injecting group_id
    new_event_list = [EventDB(**e.model_dump(exclude={"group_id"}), group_id=g_id) for e in body]

    event.crud.create_bulk_event(
        db_session,
        new_event_list,
    )

    await db_session.flush()

    response = GroupEvent(group_id=g_id, events=[Event.model_validate(db_event) for db_event in new_event_list])

    await db_session.commit()
    return response


@router.post(
    "/group/{group_id}",
    description="Adds an event to an existing group",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"description": "Group doesn't exist."}},
    operation_id="add_event_to_group",
    dependencies=[Depends(perm_admin)],
)
async def add_event_to_group(db_session: database.DBSession, group_id: uuid.UUID, new_event: EventCreate):

    # NOTE: There is a race condition here:
    # If the group is deleted after the existence check this will still insert the new event.
    group = await event.crud.get_events_by_group_id(db_session, group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group doesn't exist.")

    create_event = EventDB(**new_event.model_dump(), group_id=group_id)
    event.crud.create_event(db_session, create_event)
    await db_session.commit()
    await db_session.refresh(create_event)
    return create_event


@router.patch(
    "/{eid}",
    description="Update an Event detail",
    response_model=Event,
    responses={404: {"description": "Event doesn't exist."}},
    operation_id="update_event",
    dependencies=[Depends(perm_admin)],
)
async def update_event(db_session: database.DBSession, eid: int, body: EventUpdate):
    db_event = await event.crud.get_event_by_eid(db_session, eid)
    if db_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event doesn't exist.")

    db_data = Event.model_validate(db_event)
    patch_data = body.model_dump(exclude_unset=True)

    try:
        updated = Event.model_validate(db_data.model_dump() | patch_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=jsonable_encoder(e.errors())
        ) from e

    for key, value in patch_data.items():
        setattr(db_event, key, value)

    await db_session.commit()

    return updated


@router.delete(
    "/{eid}",
    description="Delete an event",
    response_model=EventDelete,
    responses={404: {"description": "Event doesn't exist."}},
    operation_id="delete_event",
    dependencies=[Depends(perm_admin)],
)
async def delete_event(db_session: database.DBSession, eid: int):
    deleted_eid = await event.crud.delete_event(db_session, eid)

    if deleted_eid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event doesn't exist.")

    await db_session.commit()
    return EventDelete(result=True, eid=deleted_eid)


@router.delete(
    "/group/{group_id}",
    description="Delete event(s) with the given group_id",
    response_model=GroupEventDeleteResponse,
    responses={404: {"description": "Event doesn't exist."}},
    operation_id="delete_group_event",
    dependencies=[Depends(perm_admin)],
)
async def delete_group_event(db_session: database.DBSession, group_id: uuid.UUID):
    deleted_eids = await event.crud.delete_group_events(db_session, group_id)

    if not deleted_eids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event doesn't exist.")

    await db_session.commit()
    return GroupEventDeleteResponse(result=True, group_id=group_id, deleted_eids=deleted_eids)
