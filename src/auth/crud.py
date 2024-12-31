import logging
from datetime import datetime, timedelta

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from auth.tables import SiteUser, UserSession
from auth.types import SessionType, SiteUserData

_logger = logging.getLogger(__name__)

async def create_user_session(
    db_session: AsyncSession,
    session_id: str,
    computing_id: str,
    session_type: str,
) -> None:
    """
    Updates the past user session if one exists, so no duplicate sessions can ever occur.

    Also, adds the new user to the SiteUser table if it's their first time logging in.
    """
    existing_user_session = await db_session.scalar(
        sqlalchemy
        .select(UserSession)
        .where(UserSession.computing_id == computing_id)
    )
    existing_user = await db_session.scalar(
        sqlalchemy
        .select(SiteUser)
        .where(SiteUser.computing_id == computing_id)
    )

    if existing_user is None:
        if existing_user_session is not None:
            # log this strange case that shouldn't be possible
            _logger.warning(f"User session {session_id} exists for non-existent user {computing_id} ... !")

        # add new user to User table if it's their first time logging in
        db_session.add(SiteUser(
            computing_id=computing_id,
            first_logged_in=datetime.now(),
            last_logged_in=datetime.now()
        ))

    if existing_user_session is not None:
        existing_user_session.issue_time = datetime.now()
        existing_user_session.session_id = session_id
        query = sqlalchemy.select(SiteUser).where(SiteUser.computing_id == computing_id)
        existing_user = (await db_session.scalars(query)).first()
        if existing_user is None:
            # log this strange case
            _logger.warning(f"User session {session_id} exists for non-existent user {computing_id}!")

            # create a user for this session
            new_user = SiteUser(
                computing_id=computing_id,
                first_logged_in=datetime.now(),
                last_logged_in=datetime.now(),
            )
            db_session.add(new_user)
        else:
            # update the last time the user logged in to now
            existing_user.last_logged_in = datetime.now()
    else:
        db_session.add(UserSession(
            computing_id=computing_id,
            issue_time=datetime.now(),
            session_id=session_id,
            session_type=session_type,
        ))

        # add new user to User table if it's their first time logging in
        query = sqlalchemy.select(SiteUser).where(SiteUser.computing_id == computing_id)
        existing_user = (await db_session.scalars(query)).first()
        if existing_user is None:
            new_user = SiteUser(
                computing_id=computing_id,
                first_logged_in=datetime.now(),
                last_logged_in=datetime.now()
            )
            db_session.add(new_user)


async def remove_user_session(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    user_session = await db_session.scalars(query)
    await db_session.delete(user_session.first())


async def get_computing_id(db_session: AsyncSession, session_id: str) -> str | None:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    existing_user_session = await db_session.scalar(query)
    return existing_user_session.computing_id if existing_user_session else None


async def get_session_type(db_session: AsyncSession, session_id: str) -> str | None:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    existing_user_session = await db_session.scalar(query)
    return existing_user_session.session_type if existing_user_session else None


# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession):
    one_day_ago = datetime.now() - timedelta(days=0.5)

    query = sqlalchemy.delete(UserSession).where(UserSession.issue_time < one_day_ago)
    await db_session.execute(query)
    await db_session.commit()


# get the site user given a session ID; returns None when session is invalid
async def get_site_user(db_session: AsyncSession, session_id: str) -> None | SiteUserData:
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

    return SiteUserData(
        user_session.computing_id,
        user.first_logged_in.isoformat(),
        user.last_logged_in.isoformat(),
        user.profile_picture_url
    )


async def site_user_exists(db_session: AsyncSession, computing_id: str) -> bool:
    user = await db_session.scalar(
        sqlalchemy
        .select(SiteUser)
        .where(SiteUser.computing_id == computing_id)
    )
    return user is not None


# update the optional user info for a given site user (e.g., display name, profile picture, ...)
async def update_site_user(
    db_session: AsyncSession,
    session_id: str,
    profile_picture_url: str
) -> bool:
    query = (
        sqlalchemy
        .select(UserSession)
        .where(UserSession.session_id == session_id)
    )
    user_session = await db_session.scalar(query)
    if user_session is None:
        return False

    query = (
        sqlalchemy
        .update(SiteUser)
        .where(SiteUser.computing_id == user_session.computing_id)
        .values(profile_picture_url = profile_picture_url)
    )
    await db_session.execute(query)

    return True
