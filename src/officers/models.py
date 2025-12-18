from datetime import date

from pydantic import BaseModel, ConfigDict, Field

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


# Officer Info Models
class OfficerInfo(BaseModel):
    computing_id: str = Field(..., max_length=COMPUTING_ID_LEN)
    legal_name: str = Field(..., max_length=OFFICER_LEGAL_NAME_MAX)
    phone_number: str | None = None
    discord_id: str | None = None
    discord_name: str | None = None
    discord_nickname: str | None = None
    google_drive_email: str | None = None
    github_username: str | None = None


# Officer Term Models
class OfficerTermCreate(BaseModel):
    """Request body to create a new Officer Term"""

    computing_id: str = Field(..., max_length=COMPUTING_ID_LEN)
    position: str = Field(..., max_length=128)
    start_date: date
    end_date: date | None = None
    nickname: str | None = Field(None, max_length=128)
    favourite_course_0: str | None = Field(None, max_length=64)
    favourite_course_1: str | None = Field(None, max_length=64)
    favourite_pl_0: str | None = Field(None, max_length=64)
    favourite_pl_1: str | None = Field(None, max_length=64)
    biography: str | None = None
    photo_url: str | None = None


class OfficerTerm(OfficerTermCreate):
    """Response model for OfficerTerm"""

    model_config = ConfigDict(from_attributes=True)

    id: int


class OfficerTermUpdate(BaseModel):
    """Request body to patch an Officer Term"""

    computing_id: str | None = Field(..., max_length=COMPUTING_ID_LEN)
    position: str | None = Field(..., max_length=128)
    start_date: date | None = None
    end_date: date | None = None
    nickname: str | None = Field(None, max_length=128)
    favourite_course_0: str | None = Field(None, max_length=64)
    favourite_course_1: str | None = Field(None, max_length=64)
    favourite_pl_0: str | None = Field(None, max_length=64)
    favourite_pl_1: str | None = Field(None, max_length=64)
    biography: str | None = None
    photo_url: str | None = None


# Concatenated Officer Models
class OfficerBase(BaseModel):
    # TODO (#71): compute this using SFU's API & remove from being uploaded
    legal_name: str = Field(..., max_length=OFFICER_LEGAL_NAME_MAX)
    position: OfficerPositionEnum
    start_date: date
    end_date: date | None = None


class OfficerPublic(OfficerBase):
    """
    Response when fetching public officer data
    """

    is_active: bool
    nickname: str | None = None
    biography: str | None = None
    csss_email: str | None = None


class OfficerPrivate(OfficerPublic):
    """
    Response when fetching private officer data
    """

    discord_id: str | None = None
    discord_name: str | None = None
    discord_nickname: str | None = None
    computing_id: str
    phone_number: str | None = None
    github_username: str | None = None
    google_drive_email: str | None = None
    photo_url: str | None = None


class OfficerCreate(OfficerPrivate):
    favourite_course_0: str | None = Field(None, max_length=64)
    favourite_course_1: str | None = Field(None, max_length=64)
    favourite_pl_0: str | None = Field(None, max_length=64)
    favourite_pl_1: str | None = Field(None, max_length=64)


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
