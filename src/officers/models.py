from datetime import datetime

from pydantic import BaseModel

from officers.constants import OfficerPositionEnum


class BaseOfficerModel(BaseModel):
    # TODO (#71): compute this using SFU's API & remove from being uploaded
    legal_name: str
    position: OfficerPositionEnum
    start_date: datetime
    end_date: str | None = None
    csss_email: str

class PublicOfficerResponse(BaseOfficerModel):
    """
    Response when fetching public officer data
    """
    is_active: bool
    nickname: str | None = None
    discord_name: str | None = None
    discord_nickname: int | None = None
    biography: str | None = None

class PrivateOfficerResponse(PublicOfficerResponse):
    """
    Response when fetching private officer data
    """
    computing_id: str
    phone_number: str | None = None
    github_username: str | None = None
    google_drive_email: str | None = None

class OfficerTermParams(BaseModel):
    """
    Create a new officer term
    """
    computing_id: str
    position: OfficerPositionEnum
    start_date: str
