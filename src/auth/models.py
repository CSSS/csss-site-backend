from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from auth.constants import UserRole
from auth.tables import SiteUserRoleDB
from constants import COMPUTING_ID_LEN, SESSION_ID_LEN


class LoginBodyParams(BaseModel):
    service: str = Field(description="Service URL used for SFU's CAS system")
    ticket: str = Field(description="Ticket return from SFU's CAS system")


class UserBaseModel(BaseModel):
    computing_id: str = Field(..., max_length=COMPUTING_ID_LEN, description="Student's computing ID")


class UserInfo(UserBaseModel):
    model_config = ConfigDict(from_attributes=True)

    roles: list[UserRole] = Field(..., description="List of roles the user has")

    @field_validator("roles", mode="before")
    @classmethod
    def flatten_roles(cls, roles: list[UserRole] | list[object]) -> list[UserRole]:
        if not isinstance(roles, list):
            raise TypeError("`roles` must be a list")
        result: list[UserRole] = []

        for role in roles:
            if isinstance(role, UserRole):
                result.append(role)
            elif isinstance(role, SiteUserRoleDB):
                result.append(role.role)
            else:
                raise TypeError(f"Unexpected type in `roles`: {type(role)}")
        return result


class SiteUser(UserInfo):
    model_config = ConfigDict(from_attributes=True)

    first_logged_in: datetime | None = Field(..., description="Time the user was created")
    last_logged_in: datetime | None = Field(..., description="Time the user last logged in")
