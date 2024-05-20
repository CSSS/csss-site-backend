from datetime import datetime, timedelta

from auth import models

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession


# updates the past user session if there exists one, so no duplicates can ever occur
async def create_user_session(
    db_session: AsyncSession, session_id: str, computing_id: str
) -> None:
    query = sqlalchemy.select(models.UserSession).where(
        models.UserSession.computing_id == computing_id
    )
    existing_user_session = (await db_session.scalars(query)).first()
    if existing_user_session:
        existing_user_session.issue_time = datetime.now()
        existing_user_session.session_id = session_id
    else:
        new_user_session = models.UserSession(
            issue_time=datetime.now(),
            session_id=session_id,
            computing_id=computing_id,
        )
        db_session.add(new_user_session)


async def remove_user_session(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(models.UserSession).where(
        models.UserSession.session_id == session_id
    )
    user_session = await db_session.scalars(query)
    db_session.delete(user_session.first())


async def check_session_validity(db_session: AsyncSession, session_id: str) -> dict:
    query = sqlalchemy.select(models.UserSession).where(
        models.UserSession.session_id == session_id
    )
    existing_user_session = (await db_session.scalars(query)).first()

    if existing_user_session:
        return {"is_valid": True, "computing_id": existing_user_session.computing_id}
    else:
        return {"is_valid": False}


# remove all out of date user sessions
async def task_clean_expired_user_sessions(db_session: AsyncSession) -> None:
    one_day_ago = datetime.now() - timedelta(days=0.5)

    query = sqlalchemy.delete(models.UserSession).where(
        models.UserSession.issue_time < one_day_ago
    )
    await db_session.execute(query)
    await db_session.commit()
