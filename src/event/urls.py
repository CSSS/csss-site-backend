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
from datetime import datetime, date

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


@router.get(
    "/{year}",
    description="Get events that start OR end in this year",
    response_model=list[EventPublic],
    # responses= {}
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
    response_model=list[EventPublic],
    # responses= {}
    operation_id="get_events_for_this_year_month"
)
async def get_events_for_this_year_month(
    db_session: database.DBSession,
    year: int,
    month: int
):
    events_list = await event.crud.get_events_for_this_year_month(db_session, year, month)

    return events_list
