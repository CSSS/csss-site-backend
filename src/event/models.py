import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from event.constants import EventFrequencyEnum, EventStatusEnum


class BaseEvent(BaseModel):
    name: str
    description: str
    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    group_id: UUID | None = None
    location: str | None = None
    organizer: str | None = None
    status: EventStatusEnum
    url: str | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "BaseEvent":
        if self.start_datetime >= self.end_datetime:
            raise ValueError("The event start must be before the event end")
        return self


class Event(BaseEvent):
    model_config = ConfigDict(from_attributes=True)
    eid: int


class EventCreate(BaseEvent):
    pass

class GroupEventCreate(BaseModel):
    group_id: UUID
    events: list[Event]


class EventUpdate(BaseModel):
    """
    Partial patch payload for PATCH-style updates. Deliberately does NOT
    inherit from BaseEvent. Inherting from BaseEvent would also inherit the validation
    which will caude bugs for None values, to avoid that we would need a db call. Hence, 
    the validation is done in the routing layer. Every field is optional here since a client
    only sends the fields they want to change.
    """
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    description: str | None = None
    start_datetime: datetime.datetime | None = None
    end_datetime: datetime.datetime | None = None
    group_id: UUID | None = None
    location: str | None = None
    organizer: str | None = None
    status: EventStatusEnum | None = None
    url: str | None = None


class EventDelete(BaseModel):
    result: bool
    eid: int


class GroupEventDelete(BaseModel):
    result: bool
    group_id: UUID
    event_deleted: int
