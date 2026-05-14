from pydantic import BaseModel, ConfigDict
import datetime

class Event(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    eid: int
    name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    description: str | None = None
    repeat: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None

class EventPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    description: str | None = None
    repeat: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None

class EventCreate(BaseModel):
    name: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    description: str | None = None
    repeat: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None

class EventUpdate(BaseModel):
    name: str | None = None
    start_time: datetime.datetime | None = None
    end_time: datetime.datetime | None = None
    description: str | None = None
    repeat: str | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None

class EventDelete(BaseModel):
    result: bool
    eid: int