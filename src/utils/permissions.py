from enum import Enum

from fastapi import HTTPException, Request, status

import auth
import database
import officers
from officers.constants import OfficerPositionEnum

WEBSITE_ADMIN_POSITIONS: list[OfficerPositionEnum] = [
    OfficerPositionEnum.PRESIDENT,
    OfficerPositionEnum.VICE_PRESIDENT,
    OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
    OfficerPositionEnum.SYSTEM_ADMINISTRATOR,
    OfficerPositionEnum.WEBMASTER,
]


# Permissions are granted if the Enum value >= the level needed
class AdminTypeEnum(Enum):
    Election = 1
    Full = 2


async def is_user_website_admin(computing_id: str, db_session: database.DBSession) -> bool:
    for position in await officers.crud.current_officer_positions(db_session, computing_id):
        if position in WEBSITE_ADMIN_POSITIONS:
            return True

    return False


# TODO: Add an election admin version that checks the election attempting to be modified as well
async def is_user_election_officer(computing_id: str, db_session: database.DBSession) -> bool:
    """
    An current election officer has access to all election, prior election officers have no access.
    """
    officer_terms = await officers.crud.get_current_terms_by_position(db_session, OfficerPositionEnum.ELECTIONS_OFFICER)
    for officer in officer_terms:
        if computing_id == officer.computing_id:
            return True

    return False


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
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session id")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if session_computing_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no computing id")

    return session_id, session_computing_id


async def get_admin(request: Request, db_session: database.DBSession, admin_type: AdminTypeEnum) -> tuple[str, str]:
    session_id, computing_id = await get_user(request, db_session)

    if (
        not is_user_website_admin(computing_id, db_session)
        and not admin_type == AdminTypeEnum.Election
        and is_user_election_officer(computing_id, db_session)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="must be an admin")

    return (session_id, computing_id)


async def verify_update(computing_id: str, db_session: database.DBSession, target_id: str):
    if target_id != computing_id and not await is_user_website_admin(computing_id, db_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="must be an admin")
