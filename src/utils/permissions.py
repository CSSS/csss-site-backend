from collections.abc import Iterable
from enum import Enum, StrEnum

from fastapi import HTTPException, Request, status

import auth
import auth.crud
import database
import officers.crud
from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import SessionUser
from auth.tables import SiteUserRoleDB
from officers.constants import OfficerPositionEnum

WEBSITE_ADMIN_POSITIONS: list[OfficerPositionEnum] = [
    OfficerPositionEnum.PRESIDENT,
    OfficerPositionEnum.VICE_PRESIDENT,
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
    OfficerPositionEnum.SYSTEM_ADMINISTRATOR,
    OfficerPositionEnum.WEBMASTER,
]

ELECTIONS_OFFICER_POSITION = [*WEBSITE_ADMIN_POSITIONS, OfficerPositionEnum.ELECTIONS_OFFICER]

# Roles satisfy their key, plus any in their set.
ROLE_HIERARCHY: dict[UserRole, frozenset[UserRole]] = {
    UserRole.ACCESS: frozenset(UserRole),
    UserRole.ADMIN: frozenset(set(UserRole) - {UserRole.ACCESS}),
    UserRole.EXEC: frozenset({UserRole.USER}),
    # These are more side-grade roles
    UserRole.EVENT: frozenset(),
    UserRole.ELECTION: frozenset(),
    UserRole.USER: frozenset(),
}


def role_satisfies(assigned_role: UserRole, required_role: UserRole) -> bool:
    return (assigned_role == required_role) or required_role in ROLE_HIERARCHY[assigned_role]


def roles_satisfy(assigned_roles: Iterable[UserRole], required_role: UserRole) -> bool:
    return any(role_satisfies(role, required_role) for role in assigned_roles)


def has_role(user: SessionUser | None, required_role: UserRole) -> bool:
    if user is None:
        return False
    return roles_satisfy(user.roles, required_role)
