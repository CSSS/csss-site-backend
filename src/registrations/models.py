from pydantic import BaseModel

from officers.constants import OfficerPositionEnum


class RegistrationModel(BaseModel):
    position: OfficerPositionEnum
    full_name: str
    linked_in: str
    instagram: str
    email: str
    discord_username: str
    speech: str

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

