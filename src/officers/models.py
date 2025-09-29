from datetime import date

from pydantic import BaseModel, Field

from officers.constants import OFFICER_LEGAL_NAME_MAX, OfficerPositionEnum


class OfficerBaseModel(BaseModel):
    # TODO (#71): compute this using SFU's API & remove from being uploaded
    legal_name: str = Field(..., max_length=OFFICER_LEGAL_NAME_MAX)
    position: OfficerPositionEnum
    start_date: date
    end_date: date | None = None

class PublicOfficerResponse(OfficerBaseModel):
    """
    Response when fetching public officer data
    """
    is_active: bool
    nickname: str | None = None
    discord_id: str | None = None
    discord_name: str | None = None
    discord_nickname: str | None = None
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

class OfficerTermBaseModel(BaseModel):
    computing_id: str
    position: OfficerPositionEnum
    start_date: date

class OfficerTermResponse(OfficerTermBaseModel):
    id: int
    end_date: date | None = None
    favourite_course_0: str | None = None
    favourite_course_1: str | None = None
    favourite_pl_0: str | None = None
    favourite_pl_1: str | None = None
    biography: str | None = None
    photo_url: str | None = None
