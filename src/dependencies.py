from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Path, status

import auth
import auth.crud
import database
from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import SessionUser
from auth.tables import SiteUserRoleDB, UserSessionDB
from utils.permissions import role_satisfies, roles_satisfy

# Dependency to ensure years in paths are valid
# Honestly don't know if this DB will be running past year 3000
YearPath = Annotated[int, Path(ge=2000, le=3000)]

# Dependency to ensure months in paths are valid
MonthPath = Annotated[int, Path(ge=1, le=12)]


async def optional_session_user(
    db_session: database.DBSession,
    session_id: Annotated[str | None, Cookie(alias=COOKIE_SESSION_KEY)] = None,
) -> SessionUser | None:
    if session_id is None:
        return None

    return await auth.crud.get_session_user(db_session, session_id)


OptionalSessionUser = Annotated[SessionUser | None, Depends(optional_session_user)]


def optional_user_id(user: OptionalSessionUser) -> str | None:
    return user.computing_id if user else None


OptionalUserId = Annotated[str | None, Depends(optional_user_id)]


def authenticated_user(user: OptionalSessionUser) -> SessionUser:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Must be logged in.")
    return user


AuthenticatedUser = Annotated[SessionUser, Depends(authenticated_user)]


def authenticated_user_id(user: AuthenticatedUser) -> str:
    return user.computing_id


AuthenticatedUserId = Annotated[str, Depends(authenticated_user_id)]


def require_role(required_role: UserRole, detail: str):
    def dependency(user: AuthenticatedUser) -> str:
        allowed = any(role_satisfies(assigned_role, required_role) for assigned_role in user.roles)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

        return user.computing_id

    return dependency


perm_election = require_role(UserRole.ELECTION, "Must be an election officer")
perm_exec = require_role(UserRole.EXEC, "Must be an executive")
perm_event = require_role(UserRole.EVENT, "Must be an event executive")
perm_admin = require_role(UserRole.ADMIN, "Must be an admin")
perm_access = require_role(UserRole.ACCESS, "Not authorized")

ElectionOfficer = Annotated[str, Depends(perm_election)]
Exec = Annotated[str, Depends(perm_exec)]
EventExec = Annotated[str, Depends(perm_event)]
SiteAdmin = Annotated[str, Depends(perm_admin)]
AccessAdmin = Annotated[str, Depends(perm_access)]

PERMISSION_DEPENDENCIES = [
    perm_election,
    perm_exec,
    perm_event,
    perm_admin,
    perm_access,
]
