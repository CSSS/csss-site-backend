from fastapi import APIRouter, Request

from translink.crud import fetch_realtime_schedule, fetch_static_schedule, get_route_statuses
from translink.models import BusRealtimeResponse

router = APIRouter(
    prefix="/translink",
    tags=["translink"],
)


@router.get(
    "/realtime",
    description="Get the realtime TransLink bus status",
    response_description="Realtime information for bus status",
    response_model=list[BusRealtimeResponse],
    operation_id="get_realtime_schedule",
)
async def get_realtime_schedule(request: Request):
    return await fetch_realtime_schedule(request.app.state.http_client)


@router.get(
    "/static",
    description="Get the static TransLink departure schedule",
    response_description="The static departure schedule for the buses at the upper bus loop.",
    operation_id="get_static_schedule",
)
async def get_static_schedule(request: Request):
    return (await fetch_static_schedule(request.app.state.http_client)).to_dict(orient="records")


@router.get(
    "/schedule",
    description="Get the departure schedule with bus status",
    response_description="The next three depature times with bus status information.",
    response_model=list[BusRealtimeResponse],
    operation_id="get_departure_schedule",
)
async def get_departure_schedule(request: Request):
    return await get_route_statuses(request.app.state.http_client)
