from pydantic import BaseModel, ConfigDict


class Nominee(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    computing_id: str
    full_name: str
    linked_in: str
    instagram: str
    email: str
    discord_username: str


class NomineeCreate(BaseModel):
    computing_id: str
    full_name: str
    linked_in: str | None = None
    instagram: str | None = None
    email: str | None = None
    discord_username: str | None = None


class NomineeUpdate(BaseModel):
    full_name: str | None = None
    linked_in: str | None = None
    instagram: str | None = None
    email: str | None = None
    discord_username: str | None = None
