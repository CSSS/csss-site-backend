from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class BusStatus(Enum):
    Arrived = 1
    Delayed = 2
    OnTime = 3
    Cancelled = 4


class TransLinkStaticScheduleEntry(BaseModel):
    trip_id: str = Field(..., description="The GTFS Trip ID for this bus.")
    route_id: str = Field(..., description="The GTFS Route ID for this bus.")
    bus_number: str = Field(..., description="The bus route number.")
    departure_seconds: int = Field(..., description="The number of seconds after midnight for this departure.")
    departure_time: str = Field(..., description="Time that the bus is departing as a HH:MM:SS string.")


class TransLinkStaticResponse(BaseModel):
    date_fetched: date = Field(
        ...,
        description="The date derived from the app's TZ_INFO (most likely America/Vancouver)",
    )
    schedule: list[TransLinkStaticScheduleEntry] = Field(
        ..., description="The static departure schedule for the buses at the upper bus loop."
    )


class TransLinkRealtimeResponse(BaseModel):
    route_number: str = Field(..., description="The bus route number.")
    scheduled_departure_time: int = Field(
        ..., description="Unix timestamp for the scheduled departure time, in seconds."
    )
    realtime_time: int = Field(..., description="Unix timestamp for the buses actual arrival time, in seconds.")
    delay_seconds: int = Field(
        ...,
        description="How delayed the bus is, in seconds. Positive numbers indicate the bus is late, negative is early.",
    )


class TransLinkScheduleResponse(TransLinkRealtimeResponse):
    status: BusStatus = Field(
        ...,
        description="Enum that indicates if the bus has arrived (1), is delayed (2), is on time (3), or cancelled (4).",
    )
