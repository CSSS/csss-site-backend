from pydantic import BaseModel, ConfigDict, model_validator
import datetime

class Event(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    eid: int
    name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    description: str | None = None
    repeat: str | None = None
    repeat_start_date: datetime.date | None = None
    repeat_end_date: datetime.date | None = None

class EventCreate(BaseModel):
    name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    description: str | None = None
    repeat: str | None = None
    repeat_start_date: datetime.date | None = None
    repeat_end_date: datetime.date | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "EventCreate":
        if self.start_time >= self.end_time:
            raise ValueError("The event start must be before the event end")
        
        if self.repeat_start_date and self.repeat_end_date:
            if self.repeat_start_date > self.repeat_end_date:
                raise ValueError("The event repeat start date must be before the end date")
        
        if self.repeat_start_date and not self.repeat_end_date:
            raise ValueError("The event can't have start date but not end date")

        if not self.repeat_start_date and self.repeat_end_date:
            raise ValueError("The event can't have end date but not start date")

        return self

class EventUpdate(BaseModel):
    name: str | None = None
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    description: str | None = None
    repeat: str | None = None
    repeat_start_date: datetime.date | None = None
    repeat_end_date: datetime.date | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "EventUpdate":
        if self.start_time and self.end_time:
            if self.start_time > self.end_time:
                raise ValueError("The event start time must be before end time")
        return self

class EventDelete(BaseModel):
    result: bool
    eid: int