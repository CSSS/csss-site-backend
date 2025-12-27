from datetime import date
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from constants import COMPUTING_ID_LEN
from officers.constants import OFFICER_LEGAL_NAME_MAX, OfficerPosition, OfficerPositionEnum
from officers.tables import OfficerInfoDB, OfficerTermDB

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
    model_config = ConfigDict(from_attributes=True)
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
    position: OfficerPositionEnum = Field(..., max_length=128)
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

    computing_id: str | None = Field(None, max_length=COMPUTING_ID_LEN)
    position: OfficerPositionEnum | None = Field(None, max_length=128)
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
    nickname: str | None = None
    biography: str | None = None
    csss_email: str | None = None


class Officer(OfficerBase):
    @classmethod
    def public_fields(cls, term: OfficerTermDB, info: OfficerInfoDB) -> Self:
        return cls(
            legal_name=info.legal_name,
            is_active=True,
            position=term.position,
            start_date=term.start_date,
            end_date=term.end_date,
            biography=term.biography,
            csss_email=OfficerPosition.to_email(term.position),
        )

    is_active: bool

    # Private Info
    discord_id: str | None = None
    discord_name: str | None = None
    discord_nickname: str | None = None
    computing_id: str | None = None
    phone_number: str | None = None
    github_username: str | None = None
    google_drive_email: str | None = None
    photo_url: str | None = None


class OfficerCreate(OfficerBase):
    """
    Parameters when creating a new Officer
    """

    computing_id: str

    discord_id: str | None = None
    discord_name: str | None = None
    discord_nickname: str | None = None
    phone_number: str | None = None
    github_username: str | None = None
    google_drive_email: str | None = None
    photo_url: str | None = None
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
