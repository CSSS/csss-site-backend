from enum import Enum
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

import auth
import database
import officers
from officers.constants import OfficerPositionEnum
from permission.types import WEBSITE_ADMIN_POSITIONS


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
    """gets the user's computing_id, or raises an exception if the current request is not logged in"""
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session id")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if session_computing_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no computing id")

    return session_id, session_computing_id


# Allows path functions to use this without having to add a bunch of checks
SessionUser = Annotated[tuple[str, str], Depends(get_user)]


async def get_admin(
    db_session: database.DBSession, session_user: SessionUser, admin_type: AdminTypeEnum
) -> tuple[str, str]:
    session_id, computing_id = session_user
    # Website admins have full permissions
    if is_user_website_admin(computing_id, db_session):
        return (session_id, computing_id)

    # Election officers have lower permissions
    if admin_type == AdminTypeEnum.Election and is_user_election_officer(computing_id, db_session):
        return (session_id, computing_id)

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="must be an admin")


# Allows path functions to use this without having to add a bunch of checks
SessionAdmin = Annotated[tuple[str, str], Depends(get_admin)]
