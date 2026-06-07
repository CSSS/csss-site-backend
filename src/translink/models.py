from enum import StrEnum

from pydantic import BaseModel


class BusStatus(StrEnum):
    INCOMING_AT = "INCOMING_AT"
    STOPPED_AT = "STOPPED_AT"
    IN_TRANSIT_TO = "IN_TRANSIT_TO"


class BusScheduleEntry(BaseModel):
    bus_number: str
    scheduled_departure_time: int
    realtime_time: int
    delay_seconds: int
    status: BusStatus
