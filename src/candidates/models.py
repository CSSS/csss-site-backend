from pydantic import BaseModel, ConfigDict


class Candidate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    computing_id: str
    nominee_election: str
    position: str
    speech: str | None = None


class CandidateCreate(BaseModel):
    computing_id: str
    position: str
    speech: str | None = None


class CandidateUpdate(BaseModel):
    position: str | None = None
    speech: str | None = None
