from enum import StrEnum

from pydantic import BaseModel, Field

from officers.types import OfficerPositionEnum


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
    available_positions: list[str]
    status: ElectionStatusEnum

    survey_link: str | None = Field(None, description="Only available to admins")
    candidates: list[CandidateModel] | None = Field(None, description="Only available to admins")

class ElectionParams(BaseModel):
    slug: str
    name: str
    type: ElectionTypeEnum
    datetime_start_nominations: str
    datetime_start_voting: str
    datetime_end_voting: str
    available_positions: list[str] | None = None
    survey_link: str | None = None

class NomineeInfoModel(BaseModel):
    computing_id: str
    full_name: str
    linked_in: str
    instagram: str
    email: str
    discord_username: str

class RegistrationParams(BaseModel):
    election_name: str
    computing_id: str
    position: OfficerPositionEnum

class RegistrationUpdateParams(RegistrationParams):
    speech: str | None = None

class RegistrantModel(BaseModel):
    computing_id: str
    nominee_election: str
    position: str
    speech: str
