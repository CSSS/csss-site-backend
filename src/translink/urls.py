from fastapi import APIRouter, Request

from translink.crud import fetch_realtime_schedule, fetch_static_schedule, get_next_departures
from translink.models import BusScheduleEntry

router = APIRouter(
    prefix="/translink",
    tags=["translink"],
)


@router.get(
    "/realtime",
    description="Get TransLink bus schedule",
    response_description="Realtime information for bus schedules",
    response_model=list[BusScheduleEntry],
    operation_id="get_realtime_schedule",
)
async def get_realtime_schedule(request: Request):
    return await fetch_realtime_schedule(request.app.state.http_client)


@router.get(
    "/static",
    description="Get the static TransLink schedule",
    response_description="Static TransLink schedule",
    operation_id="get_static_schedule",
)
async def get_static_schedule(request: Request):
    schedule = await fetch_static_schedule(request.app.state.http_client)
    return get_next_departures(schedule).to_dict(orient="records")


@router.get(
    "/schedule",
    description="Get a combination of the ",
    response_description="Static TransLink schedule",
    operation_id="get_bus_schedule",
)
async def get_bus_schedule(request: Request):
    schedule = await fetch_static_schedule(request.app.state.http_client)
    return get_next_departures(schedule).to_dict(orient="records")
