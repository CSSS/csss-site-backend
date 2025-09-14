from pydantic import BaseModel


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

