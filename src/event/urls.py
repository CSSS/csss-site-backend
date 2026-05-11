from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

import database
import event.crud
from event.models import (
    Event,
    EventPublic,
    EventCreate,
    EventUpdate
)
from event.tables import EventDB
from utils.shared_models import DetailModel, SuccessResponse

router = APIRouter(
    prefix="/event",
    tags=["event"],
)

@router.get(
    "",
    description="Get all events",
    response_model=list[EventPublic],
    # responses={},
    operation_id="get_all_events",
    # probably want it to be public so no dependecies?
    # dependecies=[Depends()] 
)
async def get_all_events(
    db_session: database.DBSession,
):
    events_list = await event.crud.get_all_events(db_session)

    return events_list