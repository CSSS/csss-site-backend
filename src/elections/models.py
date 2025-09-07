from enum import StrEnum

from pydantic import BaseModel


class ElectionTypeEnum(StrEnum):
    GENERAL = "general_election"
    BY_ELECTION = "by_election"
    COUNCIL_REP = "council_rep_election"

class ElectionModel(BaseModel):
    slug: str
    name: str
    type: ElectionTypeEnum
    datetime_start_nominations: str
    datetime_start_voting: str
    datetime_end_voting: str
    available_positions: str
    survey_link: str | None = None

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
