import logging
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import sqlalchemy
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import REDIRECT_TTL, SESSION_MAX_AGE
from auth.tables import AuthRedirectDB, SiteUserDB, SiteUserRoleDB, UserSessionDB

_logger = logging.getLogger(__name__)


def _hash_session_id(session_id: str) -> bytes:
    return sha256(session_id.encode("utf-8")).digest()


async def create_user_session(db_session: AsyncSession, session_id: str, computing_id: str) -> bytes:
    """
    Adds the new user to the SiteUser table if it's their first time logging in.

    A user can have multiple sessions.
    """
    now = datetime.now(UTC)

    session_hash = _hash_session_id(session_id)

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

    # Create a new session
    user_session = UserSessionDB(
        session_hash=session_hash,
        computing_id=computing_id,
        created_at=now,
        expires_at=now + SESSION_MAX_AGE,
    )
    db_session.add(user_session)

    return session_hash


async def remove_user_session_by_id(db_session: AsyncSession, session_id: str):
    session_hash = _hash_session_id(session_id)
    user_session = await db_session.get(UserSessionDB, session_hash)
    if user_session is not None:
        await db_session.delete(user_session)


async def remove_user_session_by_hash(db_session: AsyncSession, session_hash: bytes):
    user_session = await db_session.get(UserSessionDB, session_hash)
    if user_session is not None:
        await db_session.delete(user_session)


async def get_session_computing_id(db_session: AsyncSession, session_id: str) -> str | None:
    """
    Retrieves the computing ID from a session.

    Args:
        db_session: database transaction
        session_id: session ID the computing ID is using

    Returns:
        The computing ID associated with the session, or None if the session is invalid or expired.
    """
    session_hash = _hash_session_id(session_id)
    user_session = await db_session.get(UserSessionDB, session_hash)

    if not user_session or user_session.expires_at < datetime.now(UTC):
        return None

    return user_session.computing_id


# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession):
    query = sqlalchemy.delete(UserSessionDB).where(UserSessionDB.expires_at < datetime.now(UTC))
    await db_session.execute(query)
    await db_session.commit()


# get the site user given a session ID; returns None when session is invalid
async def get_site_user(db_session: AsyncSession, session_id: str) -> SiteUserDB | None:
    session_hash = _hash_session_id(session_id)
    user_session = await db_session.get(UserSessionDB, session_hash)

    if user_session is None or user_session.expires_at < datetime.now(UTC):
        return None

    return await db_session.get(SiteUserDB, user_session.computing_id)


async def site_user_exists(db_session: AsyncSession, computing_id: str) -> bool:
    user = await db_session.get(SiteUserDB, computing_id)
    return user is not None


def create_auth_redirect(db_session: AsyncSession, token: str, return_to: str) -> None:
    entry = AuthRedirectDB(
        id=token,
        return_to=return_to,
        expires_at=datetime.now(UTC) + timedelta(seconds=REDIRECT_TTL),
    )
    db_session.add(entry)


async def get_auth_redirect(db_session: AsyncSession, token: str) -> AuthRedirectDB | None:
    return await db_session.get(AuthRedirectDB, token)


async def delete_auth_redirect(db_session: AsyncSession, token: str) -> str | None:
    """
    Atomically deletes the auth redirect entry, returning the redirect URL of the deleted entry.

    Args:
        db_session: database transaction
        token: token to delete

    Returns:
        The redirect URL of the now deleted entry.
    """
    query = (
        sqlalchemy.delete(AuthRedirectDB)
        .where(AuthRedirectDB.id == token, AuthRedirectDB.expires_at >= datetime.now(UTC))
        .returning(AuthRedirectDB.return_to)
    )
    return await db_session.scalar(query)


async def get_user_roles(db_session: AsyncSession, computing_id: str) -> list[SiteUserRoleDB]:
    roles = await db_session.execute(
        sqlalchemy.select(SiteUserRoleDB).where(SiteUserRoleDB.computing_id == computing_id)
    )

    return list(roles.scalars().all())
