import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import IntegrityError

import database
import event.crud
import image_asset.crud
from dependencies import MonthPath, YearPath, perm_admin
from event.models import (
    Event,
    EventCreate,
    EventDelete,
    EventUpdate,
    GetEventQueryParams,
    GroupEvent,
    GroupEventDeleteResponse,
)
from event.tables import EventDB
from image_asset.tables import ImageAssetDB
from utils.shared_models import DetailModel

router = APIRouter(
    prefix="/event",
    tags=["event"],
)


@router.get(
    "",
    description="Get events, with parameters",
    response_model=list[Event],
    operation_id="get_events",
)
async def get_all_events(db_session: database.DBSession, q: Annotated[GetEventQueryParams, Query()]):
    events_list = await event.crud.get_events(db_session, q)
    return events_list


@router.post(
    "",
    description="Create a new event",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Image asset doesn't exist.", "model": DetailModel},
        500: {"description": "Failed to fetch new event", "model": DetailModel},
    },
    operation_id="create_event",
    dependencies=[Depends(perm_admin)],
)
async def create_event(db_session: database.DBSession, body: EventCreate):
    image_url = None
    if body.image_id:
        image = await image_asset.crud.get_image_asset_by_id(db_session, body.image_id)
        if image is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image asset doesn't exist.")
        image_url = event.crud.make_image_url(image.storage_key)
    new_event = EventDB(**body.model_dump())
    event.crud.create_event(
        db_session,
        new_event,
    )

    await db_session.commit()
    await db_session.refresh(new_event)

    response = Event.model_validate(new_event)
    response.image_url = image_url

    return response


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
    responses={
        400: {"description": "Image asset doesn't exist."},
        404: {"description": "Event doesn't exist."},
        409: {"description": "Concurrent change caused an issue."},
    },
    operation_id="update_event",
    dependencies=[Depends(perm_admin)],
)
async def update_event(db_session: database.DBSession, eid: int, body: EventUpdate):
    result = await event.crud.get_event_with_image_url(db_session, eid)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event doesn't exist.")

    db_event, image_url = result

    event_data = Event.model_validate(db_event).model_copy(update={"image_url": image_url})
    patch_data = body.model_dump(exclude_unset=True)  # does not include image_url
    updated_data = event_data.model_dump() | patch_data

    if "image_id" in patch_data and patch_data["image_id"] != db_event.image_id:
        new_image_id = patch_data["image_id"]

        # The patched data explicitly set image_id to None, so clear the image.
        if new_image_id is None:
            updated_data["image_url"] = None
        else:
            image = await db_session.get(ImageAssetDB, new_image_id, with_for_update=True)
            if image is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image asset doesn't exist.",
                )
            updated_data["image_url"] = event.crud.make_image_url(image.storage_key)

    try:
        updated = Event.model_validate(updated_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=jsonable_encoder(
                e.errors(),
            ),
        ) from e

    for key, value in patch_data.items():
        setattr(db_event, key, value)

    try:
        await db_session.commit()
    except IntegrityError as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Error when committing.",
        ) from e

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
