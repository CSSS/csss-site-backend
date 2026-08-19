from enum import Enum, StrEnum

from fastapi import HTTPException, Request, status

import auth
import auth.crud
import database
import officers.crud
from auth.constants import COOKIE_SESSION_KEY, UserRole
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


# Permissions are granted if the Enum value >= the level needed
class AdminTypeEnum(Enum):
    Election = 1
    Full = 2


async def is_user_website_admin(computing_id: str, db_session: database.DBSession) -> bool:
    return len(await officers.crud.current_officer_positions(db_session, computing_id, WEBSITE_ADMIN_POSITIONS)) > 0


# Roles satisfy their key, plus any in their set.
ROLE_HIERARCHY: dict[UserRole, set[UserRole]] = {
    UserRole.ADMIN: {UserRole.EXEC, UserRole.USER},
    UserRole.EXEC: {UserRole.USER},
    UserRole.USER: set(),
}


def role_satisfies(user_role: UserRole, required_role: UserRole) -> bool:
    return (user_role == required_role) or required_role in ROLE_HIERARCHY[user_role]


async def roles_satisfy(db_session: database.DBSession, computing_id: str, required_role: UserRole) -> bool:
    """
    Check if any of the user's roles satisfy the required role.

    Args:
        db_session: The database session.
        computing_id: The computing ID of the user.
        required_role: The role to satisfy.

    Returns:
        True if any of the user's roles satisfies the requirement, false otherwise.
    """
    user_roles = await auth.crud.get_user_roles(db_session, computing_id)
    return any(role_satisfies(user_role.role, required_role) for user_role in user_roles)


async def is_user_role(db_session: database.DBSession, computing_id: str, role: UserRole) -> bool:
    roles = await db_session.get(SiteUserRoleDB, (computing_id, role))
    return roles is not None


# TODO: Add an election admin version that checks the election attempting to be modified as well
async def is_user_election_admin(computing_id: str, db_session: database.DBSession) -> bool:
    """
    An current election officer has access to all election, prior election officers have no access.
    """
    return len(await officers.crud.current_officer_positions(db_session, computing_id, ELECTIONS_OFFICER_POSITION)) > 0


async def get_user(request: Request, db_session: database.DBSession) -> tuple[str, str]:
    """
    Get the user's computing ID and session ID.

    Args:
        request: The request
        db_session: Database session

    Returns:
        A tuple of (session_id, computing_id)

    Raises:
        HTTPException: User is not logged in
    """
    session_id = request.cookies.get(COOKIE_SESSION_KEY, None)
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session id")

    session_computing_id = await auth.crud.get_session_computing_id(db_session, session_id)
    if session_computing_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no computing id")

    return session_id, session_computing_id


async def get_admin(request: Request, db_session: database.DBSession, admin_type: AdminTypeEnum) -> tuple[str, str]:
    session_id, computing_id = await get_user(request, db_session)

    if (admin_type == AdminTypeEnum.Full and not await is_user_website_admin(computing_id, db_session)) or (
        admin_type == AdminTypeEnum.Election and not await is_user_election_admin(computing_id, db_session)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="must be an admin")

    return (session_id, computing_id)


async def verify_update(computing_id: str | None, db_session: database.DBSession, target_id: str):
    if not computing_id or (target_id != computing_id and not await is_user_website_admin(computing_id, db_session)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="must be an admin")
