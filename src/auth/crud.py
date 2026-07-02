import logging
from datetime import UTC, datetime

import sqlalchemy
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import SESSION_MAX_AGE
from auth.tables import SiteUserDB, UserSessionDB

_logger = logging.getLogger(__name__)


async def create_user_session(db_session: AsyncSession, session_id: str, computing_id: str):
    """
    Updates the past user session if one exists, so no duplicate sessions can ever occur.

    Also, adds the new user to the SiteUser table if it's their first time logging in.
    """
    now = datetime.now(UTC)

    # Upsert the site user
    # Create a new user if it's their first login...
    user_query = insert(SiteUserDB).values(
        computing_id=computing_id,
        first_logged_in=now,
        last_logged_in=now,
    )
    # ...or just update their "last_logged_in" time
    user_query = user_query.on_conflict_do_update(
        index_elements=[SiteUserDB.computing_id], set_={"last_logged_in": now}
    )
    await db_session.execute(user_query)

    # Upsert the user session
    # Create a new session...
    session_query = insert(UserSessionDB).values(
        session_id=session_id,
        computing_id=computing_id,
        issue_time=now,
    )
    # ...or update their current session
    session_query = session_query.on_conflict_do_update(
        index_elements=[UserSessionDB.computing_id], set_={"session_id": session_id, "issue_time": now}
    )
    await db_session.execute(session_query)


async def remove_user_session(db_session: AsyncSession, session_id: str):
    query = sqlalchemy.select(UserSessionDB).where(UserSessionDB.session_id == session_id)
    user_session = await db_session.scalar(query)
    if user_session is not None:
        await db_session.delete(user_session)


async def get_computing_id(db_session: AsyncSession, session_id: str) -> str | None:
    query = sqlalchemy.select(UserSessionDB).where(UserSessionDB.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()
    return existing_user_session.computing_id if existing_user_session else None


# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession):
    expiration = datetime.now(UTC) - SESSION_MAX_AGE

    query = sqlalchemy.delete(UserSessionDB).where(UserSessionDB.issue_time < expiration)
    await db_session.execute(query)
    await db_session.commit()


# get the site user given a session ID; returns None when session is invalid
async def get_site_user(db_session: AsyncSession, session_id: str) -> SiteUserDB | None:
    query = sqlalchemy.select(UserSessionDB).where(UserSessionDB.session_id == session_id)
    user_session = await db_session.scalar(query)
    if user_session is None:
        return None

    query = sqlalchemy.select(SiteUserDB).where(SiteUserDB.computing_id == user_session.computing_id)
    return await db_session.scalar(query)


async def site_user_exists(db_session: AsyncSession, computing_id: str) -> bool:
    user = await db_session.get(SiteUserDB, computing_id)
    return user is not None
