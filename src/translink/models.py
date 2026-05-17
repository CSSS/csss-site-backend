from enum import StrEnum

from pydantic import BaseModel, Field


class BusStatus(StrEnum):
    INCOMING_AT = "INCOMING_AT"  # The vehicle is going to stop at the next bus stop
    STOPPED_AT = "STOPPED_AT"  # The vehicle is currently waiting at a bus stop
    IN_TRANSIT_TO = "IN_TRANSIT_TO"  # The vehicle has departed its previous stop and in transit


class BusScheduleEntry(BaseModel):
    route_number: str = Field(..., description="The bus route number.")
    scheduled_departure_time: int = Field(..., description="Unix timestamp for the scheduled arrival time, in seconds.")
    realtime_time: int = Field(..., description="Unix timestamp for the buses actual arrival time, in seconds.")
    delay_seconds: int = Field(
        ...,
        description="How delayed the bus is, in seconds. Positive numbers indicate the bus is late, negative is early.",
    )
    status: BusStatus = Field(..., description="The bus status: incoming, stopped, or in transit to")
