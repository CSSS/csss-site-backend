import asyncio
from typing import Any, cast

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message
from google.transit import gtfs_realtime_pb2

from config import settings
from translink.crud import BUS_DATA, load_static_schedule
from translink.models import BusScheduleEntry, BusStatus
from translink.types import FeedMessage

REALTIME_URL = "https://gtfsapi.translink.ca/v3/gtfsrealtime"
POSITION_URL = "https://gtfsapi.translink.ca/v3/gtfsposition"


def get_bus_status_string(status: int) -> BusStatus:
    match status:
        case 0:
            return BusStatus.INCOMING_AT
        case 1:
            return BusStatus.STOPPED_AT
        case 2:
            return BusStatus.IN_TRANSIT_TO
        case _:
            raise ValueError(f"Unknown bus status: {status}")


async def fetch_feed(client: httpx.AsyncClient, url: str, params: dict[str, Any]):
    response = await client.get(url, params=params)
    feed = cast(FeedMessage, gtfs_realtime_pb2.FeedMessage())  # pyright: ignore[reportAttributeAccessIssue]
    feed.ParseFromString(response.content)
    return feed


router = APIRouter(
    prefix="/translink",
    tags=["translink"],
)


@router.get(
    "/schedule",
    description="Get TransLink bus schedule",
    response_description="Real-time information for bus schedules",
    response_model=list[BusScheduleEntry],
    operation_id="get_bus_schedules",
)
async def get_bus_schedules(request: Request):
    # FeedMessage is generated at runtime, so the LSP can't find this function
    params = {"apikey": settings.translink_api_key}

    trip_feed, position_feed = await asyncio.gather(
        fetch_feed(request.app.state.http_client, REALTIME_URL, params=params),
        fetch_feed(request.app.state.http_client, POSITION_URL, params=params),
    )

    vehicle_positions = {}
    for entity in position_feed.entity:
        if not entity.HasField("vehicle"):
            continue

        trip = entity.vehicle.trip
        if trip.route_id not in BUS_DATA or trip.direction_id != BUS_DATA[trip.route_id][0]:
            continue
        vehicle_positions[trip.trip_id] = entity.vehicle

    result: list[BusScheduleEntry] = []
    for entity in trip_feed.entity:
        if not entity.HasField("trip_update"):
            continue

        trip_update = entity.trip_update
        trip = trip_update.trip
        bus_data = BUS_DATA.get(trip.route_id)

        if bus_data is None or trip.direction_id != bus_data[0]:
            continue

        _, stop_id, bus_number = bus_data
        stop = next((s for s in trip_update.stop_time_update if s.stop_id == stop_id), None)
        if stop is None:
            continue

        scheduled_time = stop.departure.time - stop.departure.delay

        trip_id = trip.trip_id
        status = BusStatus.INCOMING_AT
        vehicle = vehicle_positions.get(trip_id)
        if vehicle:
            status = get_bus_status_string(vehicle.current_status)

        result.append(
            BusScheduleEntry(
                bus_number=bus_number,
                scheduled_departure_time=scheduled_time,
                realtime_time=stop.departure.time,
                delay_seconds=stop.departure.delay,
                status=status,
            )
        )

    return result


@router.get(
    "/static",
    description="Get the static TransLink schedule",
    response_description="Static TransLink schedule",
    operation_id="get_static_schedule",
)
async def get_static_schedule(request: Request):
    return (await load_static_schedule(request.app.state.http_client)).to_dict(orient="records")
