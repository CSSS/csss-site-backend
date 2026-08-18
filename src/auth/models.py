from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from constants import COMPUTING_ID_LEN, SESSION_ID_LEN


class LoginBodyParams(BaseModel):
    service: str = Field(description="Service URL used for SFU's CAS system")
    ticket: str = Field(description="Ticket return from SFU's CAS system")


class UserBaseModel(BaseModel):
    computing_id: str = Field(..., max_length=COMPUTING_ID_LEN, description="Student's computing ID")


class SiteUser(UserBaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_logged_in: datetime | None = Field(..., description="Time the user was created")
    last_logged_in: datetime | None = Field(..., description="Time the user last logged in")
