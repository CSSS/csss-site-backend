from datetime import datetime

from pydantic import BaseModel, Field


class LoginBodyParams(BaseModel):
    service: str = Field(description="Service URL used for SFU's CAS system")
    ticket: str = Field(description="Ticket return from SFU's CAS system")
    redirect_url: str | None = Field(None, description="Optional redirect URL")

class UpdateUserParams(BaseModel):
    profile_picture_url: str

class UserSessionModel(BaseModel):
    computing_id: str
    issue_time: datetime
    session_id: str

class SiteUserModel(BaseModel):
    computing_id: str
    first_logged_in: datetime
    last_logged_in: datetime
    profile_picture_url: str | None = None
