import logging
from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy
from auth.tables import SiteUser, UserSession
from sqlalchemy.ext.asyncio import AsyncSession


# TODO: put "task_" before
async def create_user_session(db_session: AsyncSession, session_id: str, computing_id: str):
    """
    Updates the past user session if one exists, so no duplicate sessions can ever occur.

    Also, adds the new user to the SiteUser table if it's their first time logging in.
    """
    query = sqlalchemy.select(UserSession).where(UserSession.computing_id == computing_id)
    existing_user_session = await db_session.scalar(query)
    if existing_user_session is not None:
        existing_user_session.issue_time = datetime.now()
        existing_user_session.session_id = session_id

        query = sqlalchemy.select(SiteUser).where(SiteUser.computing_id == computing_id)
        existing_user = await db_session.scalar(query)
        if existing_user is None:
            # log this strange case
            _logger = logging.getLogger(__name__)
            _logger.warning(f"User session {session_id} exists for non-existent user {computing_id}!")

            db_session.add(SiteUser(
                computing_id=computing_id,
                first_logged_in=datetime.now(),
                last_logged_in=datetime.now()
            ))
        else:
            # update the last time the user logged in to now
            existing_user.last_logged_in=datetime.now()
    else:
        # add new user to User table if it's their first time logging in
        query = sqlalchemy.select(SiteUser).where(SiteUser.computing_id == computing_id)
        existing_user = await db_session.scalar(query)
        if existing_user is None:
            db_session.add(SiteUser(
                computing_id=computing_id,
                first_logged_in=datetime.now(),
                last_logged_in=datetime.now()
            ))

        db_session.add(UserSession(
            session_id=session_id,
            computing_id=computing_id,
            issue_time=datetime.now(),
        ))


async def remove_user_session(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    user_session = await db_session.scalars(query)
    await db_session.delete(user_session.first())


async def check_user_session(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()

    if existing_user_session:
        query = sqlalchemy.select(SiteUser).where(SiteUser.computing_id == existing_user_session.computing_id)
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
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()
    return existing_user_session.computing_id if existing_user_session else None


# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession):
    one_day_ago = datetime.now() - timedelta(days=0.5)

    query = sqlalchemy.delete(UserSession).where(UserSession.issue_time < one_day_ago)
    await db_session.execute(query)
    await db_session.commit()


async def user_info(db_session: AsyncSession, session_id: str) -> None | dict:
    query = (
        sqlalchemy
        .select(UserSession)
        .where(UserSession.session_id == session_id)
    )
    user_session = await db_session.scalar(query)
    if user_session is None:
        return None

    query = (
        sqlalchemy
        .select(SiteUser)
        .where(SiteUser.computing_id == user_session.computing_id)
    )
    user = await db_session.scalar(query)
    if user is None:
        return None

    return {
        "computing_id": user_session.computing_id,
        "first_logged_in": user.first_logged_in.isoformat(),
        "last_logged_in": user.last_logged_in.isoformat()
    }
