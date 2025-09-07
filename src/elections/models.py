from enum import StrEnum

from pydantic import BaseModel, Field


class ElectionTypeEnum(StrEnum):
    GENERAL = "general_election"
    BY_ELECTION = "by_election"
    COUNCIL_REP = "council_rep_election"

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
    available_positions: str
    survey_link: str | None = None

    candidates: list[CandidateModel] | None = Field(None, description="Only avaiable to admins")

class ElectionParams:
    slug: str
    name: str
    type: ElectionTypeEnum
    datetime_start_nominations: str
    datetime_start_voting: str
    datetime_end_voting: str
    available_positions: list[str] | None = None
    survey_link: str | None = None

    candidates: list[CandidateModel] | None = Field(None, description="Only avaiable to admins")

class NomineeInfoModel(BaseModel):
    computing_id: str
    full_name: str
    linked_in: str
    instagram: str
    email: str
    discord_username: str

class NomineeApplicationModel(BaseModel):
    computing_id: str
    nominee_election: str
    position: str
    speech: str
