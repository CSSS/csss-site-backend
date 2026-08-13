from fastapi import APIRouter, HTTPException, Request, status

from database import DBSession
from translink.crud import (
    STATIC_CACHE_UNAVAILABLE_MESSAGE,
    StaticScheduleCacheUnavailableError,
    fetch_realtime_schedule,
    get_departure_statuses,
    get_static_schedule,
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
async def get_realtime_schedule(db_session: DBSession, request: Request):
    return await fetch_realtime_schedule(db_session, request.app.state.http_client)


@router.get(
    "/static",
    description="Get the static TransLink departure schedule.",
    response_description="The static departure schedule for the buses at the upper bus loop.",
    response_model=TransLinkStaticResponse,
    operation_id="get_static_schedule",
)
async def get_static_schedule_endpoint(db_session: DBSession):
    try:
        date_fetched, rows = await get_static_schedule(db_session)
    except StaticScheduleCacheUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STATIC_CACHE_UNAVAILABLE_MESSAGE,
        ) from e
    schedule = [TransLinkStaticScheduleEntry(**row) for row in rows]

    return TransLinkStaticResponse(date_fetched=date_fetched, schedule=schedule)


@router.get(
    "/schedule",
    description="Get the departure schedule with bus status using the preprocessed static schedule cache.",
    response_description="The next three depature times with bus status information.",
    response_model=list[TransLinkScheduleResponse],
    operation_id="get_departure_schedule",
)
async def get_departure_schedule(db_session: DBSession, request: Request):
    try:
        return await get_departure_statuses(db_session, request.app.state.http_client)
    except StaticScheduleCacheUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=STATIC_CACHE_UNAVAILABLE_MESSAGE,
        ) from e
