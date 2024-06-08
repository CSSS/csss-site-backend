import logging
from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy
from auth import models
from sqlalchemy.ext.asyncio import AsyncSession


async def create_user_session(db_session: AsyncSession, session_id: str, computing_id: str) -> None:
    """
    Updates the past user session if one exists, so no duplicate sessions can ever occur.

    Also, adds the new user to the User table if it's their first time logging in.
    """
    query = sqlalchemy.select(models.UserSession).where(models.UserSession.computing_id == computing_id)
    existing_user_session = (await db_session.scalars(query)).first()
    if existing_user_session:
        existing_user_session.issue_time = datetime.now()
        existing_user_session.session_id = session_id
        query = sqlalchemy.select(models.User).where(models.User.computing_id == computing_id)
        existing_user = (await db_session.scalars(query)).first()
        if existing_user is None:
            # log this strange case
            _logger = logging.getLogger(__name__)
            _logger.warning(f"User session {session_id} exists for non-existent user {computing_id}!")
            # create a user for this session
            new_user = models.User(
                computing_id=computing_id,
                first_logged_in=datetime.now(),
                last_logged_in=datetime.now()
            )
            db_session.add(new_user)
            pass
        else:
            # update the last time the user logged in to now
            existing_user.last_logged_in=datetime.now()
    else:
        new_user_session = models.UserSession(
            issue_time=datetime.now(),
            session_id=session_id,
            computing_id=computing_id,
        )
        db_session.add(new_user_session)

        # add new user to User table if it's their first time logging in
        query = sqlalchemy.select(models.User).where(models.User.computing_id == computing_id)
        existing_user = (await db_session.scalars(query)).first()
        if existing_user is None:
            new_user = models.User(
                computing_id=computing_id,
                first_logged_in=datetime.now(),
                last_logged_in=datetime.now()
            )
            db_session.add(new_user)


async def remove_user_session(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(models.UserSession).where(models.UserSession.session_id == session_id)
    user_session = await db_session.scalars(query)
    await db_session.delete(user_session.first())  # TODO: what to do with this result?


async def check_user_session(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(models.UserSession).where(models.UserSession.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()

    if existing_user_session:
        # TODO: replace this select with an sqlalchemy relationship access
        # see: https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html
        query = sqlalchemy.select(models.User).where(models.User.computing_id == existing_user_session.computing_id)
        existing_user = (await db_session.scalars(query)).first()
        return {
            "is_valid": True,
            "computing_id": existing_user_session.computing_id,
            "first_logged_in": existing_user.first_logged_in.isoformat(),
            "last_logged_in": existing_user.last_logged_in.isoformat()
        }
    else:
        return {"is_valid": False}


async def get_computing_id(db_session: AsyncSession, session_id: str) -> str | None:
    query = sqlalchemy.select(models.UserSession).where(models.UserSession.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()

    if existing_user_session:
        return existing_user_session.computing_id
    else:
        return None


# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession) -> None:
    one_day_ago = datetime.now() - timedelta(days=0.5)

    query = sqlalchemy.delete(models.UserSession).where(models.UserSession.issue_time < one_day_ago)
    await db_session.execute(query)
    await db_session.commit()
