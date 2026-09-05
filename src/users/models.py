from pydantic import BaseModel, Field, field_validator

from auth.constants import UserRole
from constants import COMPUTING_ID_LEN


class SiteUserCreate(BaseModel):
    computing_id: str = Field(
        ...,
        min_length=1,
        max_length=COMPUTING_ID_LEN,
        description="Computing ID of the user",
    )

    roles: list[UserRole] = Field(
        [],
        description="List of roles assigned to the user",
    )

    @field_validator("roles")
    @classmethod
    def roles_must_be_unique(cls, roles: list[UserRole]) -> list[UserRole]:
        if len(roles) != len(set(roles)):
            raise ValueError("Roles must be unique")
        return roles
