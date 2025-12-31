from pydantic import BaseModel, ConfigDict

from officers.constants import OfficerPositionEnum


class Candidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    computing_id: str
    nominee_election: str
    position: OfficerPositionEnum
    speech: str | None = None


class CandidateCreate(BaseModel):
    computing_id: str
    position: OfficerPositionEnum


class CandidateUpdate(BaseModel):
    position: OfficerPositionEnum | None = None
    speech: str | None = None
