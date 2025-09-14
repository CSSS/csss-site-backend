import re

from fastapi import HTTPException, Request, status

import auth
import auth.crud
import database
from permission.types import ElectionOfficer, WebsiteAdmin


# TODO: move other utils into this module
def slugify(text: str) -> str:
    """Creates a unique slug based on text passed in. Assumes non-unicode text."""
    return re.sub(r"[\W_]+", "-", text.strip().replace("/", "").replace("&", ""))

async def logged_in_or_raise(
    request: Request,
    db_session: database.DBSession
) -> tuple[str, str]:
    """gets the user's computing_id, or raises an exception if the current request is not logged in"""
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="no session id")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if session_computing_id is None:
        raise HTTPException(status_code=401, detail="no computing id")

    return session_id, session_computing_id

async def get_current_user(request: Request, db_session: database.DBSession) -> tuple[str, str] | tuple[None, None]:
    """
    Gets information about the currently logged in user.

    Args:
        request: The request being checked
        db_session: The current database session

    Returns:
        A tuple of either (None, None) if there is no logged in user or a tuple (session ID, computing ID)
    """
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        return None, None

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if session_computing_id is None:
        return None, None

    return session_id, session_computing_id

async def admin_or_raise(request: Request, db_session: database.DBSession) -> tuple[str, str]:
    session_id, computing_id = await get_current_user(request, db_session)
    if not session_id or not computing_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="must be logged in"
        )

    # where valid means elections officer or website admin
    if (await ElectionOfficer.has_permission(db_session, computing_id)) or (await WebsiteAdmin.has_permission(db_session, computing_id)):
        return session_id, computing_id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="must be an admin"
        )

