from fastapi import APIRouter, Request

from database import DBSession
from translink.crud import (
    fetch_realtime_schedule,
    get_departure_statuses,
    get_or_fetch_static_schedule,
)
from translink.models import (
    TransLinkRealtimeResponse,
    TransLinkScheduleResponse,
    TransLinkStaticResponse,
    TransLinkStaticScheduleEntry,
)

router = APIRouter(
    prefix="/translink",
    tags=["translink"],
)


@router.get(
    "/realtime",
    description="Get the realtime TransLink bus status.",
    response_description="Realtime information for bus status",
    response_model=list[TransLinkRealtimeResponse],
    operation_id="get_realtime_schedule",
)
async def get_realtime_schedule(request: Request):
    return await fetch_realtime_schedule(request.app.state.http_client)


@router.get(
    "/static",
    description="Get the static TransLink departure schedule.",
    response_description="The static departure schedule for the buses at the upper bus loop.",
    response_model=TransLinkStaticResponse,
    operation_id="get_static_schedule",
)
async def get_static_schedule(db_session: DBSession, request: Request):
    date_fetched, df = await get_or_fetch_static_schedule(db_session, request.app.state.http_client)
    schedule = [TransLinkStaticScheduleEntry(**row) for row in df.to_dict(orient="records")]

    return TransLinkStaticResponse(date_fetched=date_fetched, schedule=schedule)


@router.get(
    "/schedule",
    description="Get the departure schedule with bus status. Attempts to use the cached static schedule first.",
    response_description="The next three depature times with bus status information.",
    response_model=list[TransLinkScheduleResponse],
    operation_id="get_departure_schedule",
)
async def get_departure_schedule(db_session: DBSession, request: Request):
    return await get_departure_statuses(db_session, request.app.state.http_client)
