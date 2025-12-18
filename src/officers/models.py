from datetime import date

from pydantic import BaseModel, Field

from constants import COMPUTING_ID_LEN
from officers.constants import OFFICER_LEGAL_NAME_MAX, OfficerPositionEnum

OFFICER_PRIVATE_INFO = {
    "discord_id",
    "discord_name",
    "discord_nickname",
    "computing_id",
    "phone_number",
    "github_username",
    "google_drive_email",
    "photo_url",
}


class OfficerInfoBaseModel(BaseModel):
    # TODO (#71): compute this using SFU's API & remove from being uploaded
    legal_name: str = Field(..., max_length=OFFICER_LEGAL_NAME_MAX)
    position: OfficerPositionEnum
    start_date: date
    end_date: date | None = None


class OfficerInfoResponse(OfficerInfoBaseModel):
    """
    Response when fetching public officer data
    """

    is_active: bool
    nickname: str | None = None
    biography: str | None = None
    csss_email: str | None = None

    # Private data
    discord_id: str | None = None
    discord_name: str | None = None
    discord_nickname: str | None = None
    computing_id: str | None = None
    phone_number: str | None = None
    github_username: str | None = None
    google_drive_email: str | None = None
    photo_url: str | None = None


class OfficerSelfUpdate(BaseModel):
    """
    Used when an Officer is updating their own information
    """

    nickname: str | None = None
    discord_id: str | None = None
    discord_name: str | None = None
    discord_nickname: str | None = None
    biography: str | None = None
    phone_number: str | None = None
    github_username: str | None = None
    google_drive_email: str | None = None


class OfficerUpdate(OfficerSelfUpdate):
    """
    Used when an admin is updating an Officer's info
    """

    legal_name: str | None = Field(None, max_length=OFFICER_LEGAL_NAME_MAX)
    position: OfficerPositionEnum | None = None
    start_date: date | None = None
    end_date: date | None = None


class OfficerTermBaseModel(BaseModel):
    computing_id: str
    position: OfficerPositionEnum
    start_date: date


class OfficerTermCreate(OfficerTermBaseModel):
    """
    Params to create a new Officer Term
    """

    legal_name: str


class OfficerTermResponse(OfficerTermCreate):
    id: int
    end_date: date | None = None
    favourite_course_0: str | None = None
    favourite_course_1: str | None = None
    favourite_pl_0: str | None = None
    favourite_pl_1: str | None = None
    biography: str | None = None
    photo_url: str | None = None


class OfficerTermUpdate(BaseModel):
    nickname: str | None = None
    favourite_course_0: str | None = None
    favourite_course_1: str | None = None
    favourite_pl_0: str | None = None
    favourite_pl_1: str | None = None
    biography: str | None = None

    # Admin only
    position: OfficerPositionEnum | None = None
    start_date: date | None = None
    end_date: date | None = None
    photo_url: str | None = None  # Block this, just in case
