from enum import Enum

from pydantic import BaseModel, Field


class BusStatus(Enum):
    Arrived = 1
    Delayed = 2
    OnTime = 3


class BusRealtimeResponse(BaseModel):
    route_number: str = Field(..., description="The bus route number.")
    scheduled_departure_time: int = Field(..., description="Unix timestamp for the scheduled arrival time, in seconds.")
    realtime_time: int = Field(..., description="Unix timestamp for the buses actual arrival time, in seconds.")
    delay_seconds: int = Field(
        ...,
        description="How delayed the bus is, in seconds. Positive numbers indicate the bus is late, negative is early.",
    )


class BusScheduleResponse(BusRealtimeResponse):
    status: BusStatus = Field(
        ..., description="Enum that indicates if the bus has arrived (1), is delayed (2), or is on time (3)"
    )
