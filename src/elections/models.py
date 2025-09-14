from enum import StrEnum

from pydantic import BaseModel, Field

from officers.constants import OfficerPositionEnum


class ElectionTypeEnum(StrEnum):
    GENERAL = "general_election"
    BY_ELECTION = "by_election"
    COUNCIL_REP = "council_rep_election"

class ElectionStatusEnum(StrEnum):
    BEFORE_NOMINATIONS = "before_nominations"
    NOMINATIONS = "nominations"
    VOTING = "voting"
    AFTER_VOTING = "after_voting"

class CandidateModel(BaseModel):
    position: str
    full_name: str
    linked_in: str
    instagram: str
    email: str
    discord_username: str
    speech: str

class ElectionResponse(BaseModel):
    slug: str
    name: str
    type: ElectionTypeEnum
    datetime_start_nominations: str
    datetime_start_voting: str
    datetime_end_voting: str
    available_positions: list[OfficerPositionEnum]
    status: ElectionStatusEnum

    survey_link: str | None = Field(None, description="Only available to admins")
    candidates: list[CandidateModel] | None = Field(None, description="Only available to admins")

class ElectionParams(BaseModel):
    name: str
    type: ElectionTypeEnum
    datetime_start_nominations: str
    datetime_start_voting: str
    datetime_end_voting: str
    available_positions: list[OfficerPositionEnum] | None = None
    survey_link: str | None = None

class ElectionUpdateParams(BaseModel):
    type: ElectionTypeEnum | None = None
    datetime_start_nominations: str | None = None
    datetime_start_voting: str | None = None
    datetime_end_voting: str | None = None
    available_positions: list[OfficerPositionEnum] | None = None
    survey_link: str | None = None

class NomineeApplicationParams(BaseModel):
    computing_id: str
    position: OfficerPositionEnum

class NomineeApplicationUpdateParams(BaseModel):
    position: OfficerPositionEnum | None = None
    speech: str | None = None

class NomineeApplicationModel(BaseModel):
    computing_id: str
    nominee_election: str
    position: OfficerPositionEnum
    speech: str | None = None

class NomineeInfoModel(BaseModel):
    computing_id: str
    full_name: str
    linked_in: str
    instagram: str
    email: str
    discord_username: str

class NomineeInfoUpdateParams(BaseModel):
    full_name: str | None = None
    linked_in: str | None = None
    instagram: str | None = None
    email: str | None = None
    discord_username: str | None = None

