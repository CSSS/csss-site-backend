from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from constants import COMPUTING_ID_LEN, DISCORD_ID_LEN, GITHUB_USERNAME_LEN, GMAIL_MAX_LEN, PHONE_NUMBER_MAX_LEN
from officers.constants import OFFICER_NAME_MAX_LEN, OFFICER_POSITION_MAX_LEN, OfficerPositionTypeEnum
from officers.tables import OfficerPositionDB, OfficerPositionVersionDB, OfficerTermDB


class OfficerBase(BaseModel):
    legal_name: str = Field(
        ...,
        min_length=1,
        max_length=OFFICER_NAME_MAX_LEN,
        description="Legal name, for official documents",
    )

    preferred_name: str | None = Field(
        None,
        max_length=OFFICER_NAME_MAX_LEN,
        description="Name the officer prefers to be called",
    )

    start_date: date = Field(..., description="Officer's start date")

    end_date: date | None = Field(None, description="Officer's end date")

    photo_url: str | None = Field(None, description="URL to officer's photo")

    @model_validator(mode="after")
    def validate_time_range(self) -> "OfficerBase":
        if not self.start_date or not self.end_date:
            return self

        if self.start_date > self.end_date:
            raise ValueError("Event start times cannot be greater than end times")
        return self


class PublicOfficerTerm(OfficerBase):
    position: str = Field(
        ...,
        min_length=1,
        max_length=OFFICER_POSITION_MAX_LEN,
        description="Position of the officer",
    )

    @classmethod
    def from_db(cls, term: OfficerTermDB) -> "PublicOfficerTerm":
        return PublicOfficerTerm(
            legal_name=term.officer.legal_name,
            preferred_name=term.officer.preferred_name,
            start_date=term.start_date,
            end_date=term.end_date,
            position=term.position_version.position.position,
            photo_url=term.photo_url,
        )


class OfficerPrivateBase(OfficerBase):
    phone_number: str | None = Field(
        None,
        max_length=PHONE_NUMBER_MAX_LEN,
        description="Officer's phone number",
    )

    position_version_id: int = Field(
        ...,
        description="ID of the officer position version",
    )

    discord_id: str | None = Field(
        None,
        max_length=DISCORD_ID_LEN,
        description="Officer's Discord Snowflake ID",
    )

    google_drive_email: str | None = Field(
        None,
        max_length=GMAIL_MAX_LEN,
        description="Officer's personal Gmail",
    )

    github_username: str | None = Field(
        None,
        max_length=GITHUB_USERNAME_LEN,
        description="Officer's personal GitHub",
    )


class PrivateOfficerTerm(OfficerPrivateBase):
    computing_id: str | None = Field(
        None,
        max_length=COMPUTING_ID_LEN,
        description="Officer's SFU computing ID",
    )

    term_id: int = Field(
        ...,
        description="Unique ID of the officer term",
    )

    @classmethod
    def from_db(cls, term: OfficerTermDB) -> "PrivateOfficerTerm":
        return PrivateOfficerTerm(
            legal_name=term.officer.legal_name,
            preferred_name=term.officer.preferred_name,
            start_date=term.start_date,
            end_date=term.end_date,
            position_version_id=term.position_version_id,
            photo_url=term.photo_url,
            phone_number=term.officer.phone_number,
            discord_id=term.officer.discord_id,
            google_drive_email=term.officer.google_drive_email,
            github_username=term.officer.github_username,
            computing_id=term.officer.computing_id,
            term_id=term.id,
        )


class OfficerCreate(OfficerPrivateBase):
    computing_id: str = Field(
        ...,
        min_length=1,
        max_length=COMPUTING_ID_LEN,
        description="Officer's SFU computing ID",
    )


class OfficerInfoUpdate(BaseModel):
    legal_name: str | None = Field(
        None,
        min_length=1,
        max_length=OFFICER_NAME_MAX_LEN,
        description="Legal name, for official documents",
    )

    preferred_name: str | None = Field(
        None,
        max_length=OFFICER_NAME_MAX_LEN,
        description="Name the officer prefers to be called",
    )

    phone_number: str | None = Field(None, max_length=PHONE_NUMBER_MAX_LEN)

    discord_id: str | None = Field(None, max_length=DISCORD_ID_LEN)

    google_drive_email: str | None = Field(None, max_length=GMAIL_MAX_LEN)

    github_username: str | None = Field(None, max_length=GITHUB_USERNAME_LEN)

    @field_validator("legal_name")
    @classmethod
    def legal_name_cannot_be_blank(cls, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("legal_name cannot be null or blank")
        return value


class OfficerTermUpdate(BaseModel):
    position_version_id: int | None = Field(None, ge=1)

    start_date: date | None = None

    end_date: date | None = None

    photo_url: str | None = None

    @field_validator("position_version_id", "start_date")
    @classmethod
    def required_columns_cannot_be_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("field cannot be null")
        return value

    @model_validator(mode="after")
    def validate_time_range(self) -> "OfficerTermUpdate":
        if not self.start_date or not self.end_date:
            return self

        if self.start_date > self.end_date:
            raise ValueError("Officer term start times cannot be greater than end times")
        return self


class OfficerUpdate(BaseModel):
    info: OfficerInfoUpdate | None = None

    term: OfficerTermUpdate | None = None


# -----------------------
# OFFICER POSITION MODELS
# -----------------------


class OfficerPositionVersionCreate(BaseModel):
    type: OfficerPositionTypeEnum = Field(..., description="Type of officer of this position")

    multiple_allowed: bool | None = Field(
        None,
        description="Whether multiple officers can hold this Executive position at the same time",
    )

    effective_from: date = Field(..., description="Date from which this version of the position is effective")

    effective_to: date | None = Field(None, description="Date when this position stopped being used")

    @model_validator(mode="after")
    def validate_multiple_allowed(self) -> "OfficerPositionVersionCreate":
        if self.multiple_allowed is not None and self.type != OfficerPositionTypeEnum.EXECUTIVE:
            raise ValueError("multiple_allowed can only be set for Executive positions")

        if self.multiple_allowed is None and self.type == OfficerPositionTypeEnum.EXECUTIVE:
            raise ValueError("multiple_allowed must be set for Executive positions")

        return self

    @model_validator(mode="after")
    def validate_time_range(self) -> "OfficerPositionVersionCreate":
        if self.effective_to is None:
            return self

        if self.effective_to <= self.effective_from:
            raise ValueError("Officer position version effective to times must be later than their effective from date")

        return self


class OfficerPositionCreate(OfficerPositionVersionCreate):
    name: str = Field(..., min_length=1, max_length=OFFICER_POSITION_MAX_LEN, description="Name of the position")


class OfficerPosition(OfficerPositionCreate):
    position_id: int = Field(..., ge=1, description="ID of the position")

    version_id: int = Field(..., ge=1, description="Latest version number of the position")

    @classmethod
    def from_db(cls, db: OfficerPositionVersionDB) -> "OfficerPosition":
        """
        Args:
            db: Database object that has been loaded fully with the position using a `joinedload`.

        Returns:
            Response for an Officer Position.
        """
        return cls(
            position_id=db.position.id,
            version_id=db.id,
            name=db.position.position,
            type=db.type,
            multiple_allowed=db.multiple_allowed,
            effective_from=db.effective_from,
            effective_to=db.effective_to,
        )

    @classmethod
    def from_pos_and_ver(cls, position: OfficerPositionDB, version: OfficerPositionVersionDB) -> "OfficerPosition":
        return cls(
            position_id=position.id,
            version_id=version.id,
            name=position.position,
            multiple_allowed=version.multiple_allowed,
            type=version.type,
            effective_from=version.effective_from,
            effective_to=version.effective_to,
        )


class OfficerPositionUpdate(BaseModel):
    effective_to: date | None = Field(..., description="Date the role should end")

    @model_validator(mode="before")
    @classmethod
    def effective_to_required(cls, data: Any) -> Any:
        if isinstance(data, dict) and "effective_to" not in data:
            raise ValueError("effective_to is required for updating an officer position version")

        return data
