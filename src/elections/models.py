from enum import Enum

from pydantic import BaseModel


class ElectionTypeEnum(str, Enum):
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
    survey_link: str | None

