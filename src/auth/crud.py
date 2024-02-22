from datetime import datetime

import models

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

# updates the past user session if there exists one, so no duplicates can ever occur
async def create_user_session(db_session: AsyncSession, session_id: str, computing_id: str) -> None:
    query = sqlalchemy.select(models.UserSession).where(models.UserSession.computing_id == computing_id)
    existing_user_session = (await db_session.scalars(query)).first()
    if existing_user_session:
        existing_user_session.issue_time = datetime.now()
        existing_user_session.session_id = session_id
    else:
        new_user_session = models.UserSession(
            issue_time = datetime.now(),
            session_id = session_id,
            computing_id = computing_id,
        )
        db_session.add(new_user_session)

async def check_session_validity(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(models.UserSession).where(models.UserSession.session_id == session_id)
    existing_user_session = (await db_session.scalars(query)).first()

    # TODO: use a match statement?!
    if existing_user_session:
        return { "is_valid" : True, "computing_id" : existing_user_session.computing_id }
    else:
        return { "is_valid" : False }

USER_SESSION_MAX_LENGTH_SEC = 24 * 60 * 60

# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession) -> None:
    current_time = datetime.now()
    query = sqlalchemy.select(models.UserSession).where(
        (current_time - models.UserSession.issue_time).total_seconds() >= USER_SESSION_MAX_LENGTH_SEC
    )
    expired_user_sessions = await db_session.scalars(query)
    expired_user_sessions.all().delete()
    await db_session.commit()
