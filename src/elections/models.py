from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from officers.constants import OfficerPositionEnum
from registrations.models import RegistrationModel


class ElectionTypeEnum(StrEnum):
    GENERAL = "general_election"
    BY_ELECTION = "by_election"
    COUNCIL_REP = "council_rep_election"


class ElectionStatusEnum(StrEnum):
    BEFORE_NOMINATIONS = "before_nominations"
    NOMINATIONS = "nominations"
    VOTING = "voting"
    AFTER_VOTING = "after_voting"


class ElectionResponse(BaseModel):
    slug: str
    name: str
    type: ElectionTypeEnum
    datetime_start_nominations: datetime
    datetime_start_voting: datetime
    datetime_end_voting: datetime
    available_positions: list[OfficerPositionEnum]
    status: ElectionStatusEnum

    # Private fields
    survey_link: str | None = Field(None, description="Only available to admins")
    candidates: list[RegistrationModel] | None = Field(None, description="Only available to admins")


class ElectionParams(BaseModel):
    name: str
    type: ElectionTypeEnum
    datetime_start_nominations: datetime
    datetime_start_voting: datetime
    datetime_end_voting: datetime
    available_positions: list[OfficerPositionEnum] | None = None
    survey_link: str | None = None


class ElectionUpdateParams(BaseModel):
    type: ElectionTypeEnum | None = None
    datetime_start_nominations: datetime | None = None
    datetime_start_voting: datetime | None = None
    datetime_end_voting: datetime | None = None
    available_positions: list[OfficerPositionEnum] | None = None
    survey_link: str | None = None
