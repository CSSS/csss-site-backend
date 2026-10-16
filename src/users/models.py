from datetime import datetime
from itertools import chain

from pydantic import UUID4, BaseModel, ConfigDict, Field, computed_field, field_validator

from auth.constants import UserRole
from auth.tables import SiteUserRoleDB
from constants import COMPUTING_ID_LEN, SPLIT_NAME_MAX_LEN
from utils.permissions import ROLE_HIERARCHY


class UserNames(BaseModel):
    """Name fields shared by account responses and admin requests."""

    first_name: str | None = Field(None, max_length=SPLIT_NAME_MAX_LEN, description="First name of the user")

    last_name: str | None = Field(None, max_length=SPLIT_NAME_MAX_LEN, description="Last name of the user")

    preferred_name: str | None = Field(
        None, max_length=SPLIT_NAME_MAX_LEN, description="Preferred first name of the user"
    )


class UserRoles(BaseModel):
    roles: list[UserRole] = Field(description="List of roles assigned to the user")

    @field_validator("roles", mode="before")
    @classmethod
    def flatten_roles(cls, roles: list[UserRole] | list[SiteUserRoleDB]) -> list[UserRole]:
        return [role.role if isinstance(role, SiteUserRoleDB) else role for role in roles]


class UserBaseModel(UserNames, UserRoles):
    """Shared fields for private user responses; never use for public profiles."""

    model_config = ConfigDict(from_attributes=True)

    uid: UUID4 = Field(description="Public user ID")
    computing_id: str | None = Field(None, max_length=COMPUTING_ID_LEN, description="User's computing ID")


class UserInfo(UserBaseModel):
    """Current user's account information, including permissions for the interface."""

    @computed_field
    @property
    def effective_roles(self) -> list[UserRole]:
        effective_roles = set(chain(self.roles, *(ROLE_HIERARCHY[role] for role in self.roles)))
        return [role for role in UserRole if role in effective_roles]


class SiteUser(UserBaseModel):
    """Full user record for admin user management."""

    first_logged_in: datetime | None = Field(description="Time the user first logged in")
    last_logged_in: datetime | None = Field(description="Time the user last logged in")


class SiteUserCreate(UserNames):
    """Admin creation request. The server generates the UID."""

    model_config = ConfigDict(extra="forbid")

    computing_id: str = Field(min_length=1, max_length=COMPUTING_ID_LEN, description="Computing ID of the user")
    roles: list[UserRole] = Field(default_factory=list, description="List of roles assigned to the user")

    @field_validator("roles")
    @classmethod
    def roles_must_be_unique(cls, roles: list[UserRole]) -> list[UserRole]:
        if len(roles) != len(set(roles)):
            raise ValueError("Roles must be unique")
        return roles


class SiteUserUpdate(UserNames):
    """Admin update request. Omitted fields stay unchanged; null clears a name."""

    model_config = ConfigDict(extra="forbid")

    roles: list[UserRole] | None = Field(None, description="Complete set of roles assigned to the user")
