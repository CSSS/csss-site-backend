from pydantic import BaseModel, ConfigDict, model_validator
import datetime


class BaseEvent(BaseModel):
    name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    description: str | None = None
    repeat: str | None = None
    repeat_start_date: datetime.date | None = None
    repeat_end_date: datetime.date | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "BaseEvent":
        if self.start_time >= self.end_time:
            raise ValueError("The event start must be before the event end")
        
        if self.repeat_start_date and self.repeat_end_date:
            if self.repeat_start_date > self.repeat_end_date:
                raise ValueError("The event repeat start date must be before the end date")
        
        if (self.repeat_start_date is None) != (self.repeat_end_date is None):
            raise ValueError("The event must have both repeat start and repeat end or have neither.")
        
        return self

class Event(BaseEvent):
    model_config = ConfigDict(from_attributes=True)
    eid: int

class EventCreate(BaseEvent):
    pass

class EventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    description: str | None = None
    repeat: str | None = None
    repeat_start_date: datetime.date | None = None
    repeat_end_date: datetime.date | None = None

class EventDelete(BaseModel):
    result: bool
    eid: int