from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

import auth
import auth.crud
import database
from auth.constants import COOKIE_SESSION_KEY
from config import settings
from utils.permissions import is_user_election_admin, is_user_website_admin


async def optional_user(
    db_session: database.DBSession, session_id: Annotated[str | None, Cookie(alias=COOKIE_SESSION_KEY)] = None
) -> str | None:
    """
    Fetches the computing ID of the user from the user session's table.

    Args:
        db_session: The database session.
        session_id: The session ID from the request's cookie.

    Returns:
        The computing ID of the user if their session is valid.
    """
    if session_id is None:
        return None

    session_computing_id = await auth.crud.get_session_computing_id(db_session, session_id)

    return session_computing_id


OptionalUser = Annotated[str | None, Depends(optional_user)]


async def logged_in_user(
    db_session: database.DBSession, session_id: Annotated[str | None, Cookie(alias=COOKIE_SESSION_KEY)] = None
) -> str:
    """
    Fetches the computing ID of the User from the user session's table.

    Args:
        db_session: The database session.
        session_id: The session ID from the request's cookie.

    Returns:
        The computing ID of the user if their session is valid.


    Raises:
        HTTPException: If the user session doesn't exist or is expired.
    """
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session id")

    session_computing_id = await auth.crud.get_session_computing_id(db_session, session_id)
    if session_computing_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no computing id")

    return session_computing_id


LoggedInUser = Annotated[str, Depends(logged_in_user)]


async def perm_election(db_session: database.DBSession, computing_id: LoggedInUser) -> str:
    if not await is_user_website_admin(computing_id, db_session) or not await is_user_election_admin(
        computing_id, db_session
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="must be an election admin")

    return computing_id


ElectionAdmin = Annotated[str, Depends(perm_election)]


async def perm_admin(db_session: database.DBSession, computing_id: LoggedInUser):
    if not await is_user_website_admin(computing_id, db_session):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="must be an admin")

    return computing_id


SiteAdmin = Annotated[str, Depends(perm_admin)]

PERMISSION_DEPENDENCIES = [perm_election, perm_admin]
