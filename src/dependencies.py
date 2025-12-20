from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

import auth
import database
from utils.permissions import is_user_election_admin, is_user_website_admin


async def user(db_session: database.DBSession, session_id: Annotated[str | None, Cookie()] = None) -> str | None:
    if session_id is None:
        return None

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)

    return session_computing_id


SessionUser = Annotated[str, Depends(user)]


async def logged_in_user(db_session: database.DBSession, session_id: Annotated[str | None, Cookie()] = None) -> str:
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session id")

    session_computing_id = await auth.crud.get_computing_id(db_session, session_id)
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
