from datetime import datetime

from pydantic import BaseModel

from officers.constants import OfficerPositionEnum


class BaseOfficerModel(BaseModel):
    # TODO (#71): compute this using SFU's API & remove from being uploaded
    legal_name: str
    position: OfficerPositionEnum
    start_date: datetime
    end_date: str | None = None

class PublicOfficerResponse(BaseOfficerModel):
    """
    Response when fetching public officer data
    """
    is_active: bool
    nickname: str | None = None
    discord_name: str | None = None
    discord_nickname: int | None = None
    biography: str | None = None
    csss_email: str

class PrivateOfficerResponse(PublicOfficerResponse):
    """
    Response when fetching private officer data
    """
    computing_id: str
    phone_number: str | None = None
    github_username: str | None = None
    google_drive_email: str | None = None

class OfficerTermCreate(BaseOfficerModel):
    """
    Create a new Officer term
    """
    computing_id: str

class OfficerTermUpdate(BaseModel):
    """
    Update an Officer Term
    """
    legal_name: str | None = None
    position: OfficerPositionEnum | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
