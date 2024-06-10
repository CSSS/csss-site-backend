from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy
from auth.models import SiteUser, UserSession
from sqlalchemy.ext.asyncio import AsyncSession


async def create_user_session(db_session: AsyncSession, session_id: str, computing_id: str) -> None:
    """
    Updates the past user session if one exists, so no duplicate sessions can ever occur.

    Also, adds the new user to the SiteUser table if it's their first time logging in.
    """
    query = sqlalchemy.select(UserSession).where(UserSession.computing_id == computing_id)
    existing_user_session = (await db_session.scalars(query)).first()
    if existing_user_session:
        existing_user_session.issue_time = datetime.now()
        existing_user_session.session_id = session_id
    else:
        new_user_session = UserSession(
            issue_time=datetime.now(),
            session_id=session_id,
            computing_id=computing_id,
        )
        db_session.add(new_user_session)

        # add new user to User table if it's their first time logging in
        query = sqlalchemy.select(SiteUser).where(SiteUser.computing_id == computing_id)
        existing_user = (await db_session.scalars(query)).first()
        if existing_user is None:
            new_user = SiteUser(
                computing_id=computing_id,
            )
            db_session.add(new_user)


async def remove_user_session(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    user_session = await db_session.scalars(query)
    await db_session.delete(user_session.first())  # TODO: what to do with this result that we're awaiting?


async def check_session_validity(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()

    if existing_user_session:
        return {"is_valid": True, "computing_id": existing_user_session.computing_id}
    else:
        return {"is_valid": False}


async def get_computing_id(db_session: AsyncSession, session_id: str) -> str | None:
    query = sqlalchemy.select(UserSession).where(UserSession.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()
    return existing_user_session.computing_id if existing_user_session else None


# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession) -> None:
    one_day_ago = datetime.now() - timedelta(days=0.5)

    query = sqlalchemy.delete(UserSession).where(UserSession.issue_time < one_day_ago)
    await db_session.execute(query)
    await db_session.commit()
