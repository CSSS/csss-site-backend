from fastapi import HTTPException, Request

import auth
import auth.crud
import database

# TODO: move other utils into this module

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

async def is_logged_in(
    request: Request,
    db_session: database.DBSession
) -> tuple[bool, str | None, str | None]:
    """gets the user's computing_id, or raises an exception if the current request is not logged in"""
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        return False, None, None

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if session_computing_id is None:
        return False, None, None

    return True, session_id, session_computing_id
