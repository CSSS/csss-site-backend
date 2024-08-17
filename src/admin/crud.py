from datetime import datetime
import sqlalchemy
from admin.models import AdminLog
from sqlalchemy.ext.asyncio import AsyncSession

from permission.types import WebsiteAdmin

async def task_insert_admin_log(
    db_session: AsyncSession,
    computing_id: str,
    description: str
) -> bool:
    """
    Returns False if the log was not inserted
    """
    # TODO: do we even need this check?
    if not WebsiteAdmin.has_permission(db_session, computing_id):
        _logger.warning(f"Tried to create admin log for non-admin user {computing_id}")
        return False

    new_log = AdminLog(
       computing_id = computing_id,
       log_time = datetime.now(),
       log_description = description,
    )

    db_session.add(new_log)
    await db_session.commit()
    
    return True


async def read_admin_log(
    db_session: AsyncSession,
    page_size: int,
    page_number: int,
) -> list[AdminLog]:
    """
    This function may only be called by admins 
    """
    # TODO: order by log_id?
    query = (
        sqlalchemy
        .select(AdminLog)
        .limit(page_size)
        .offset(page_number * page_size)
    )

    return list(db_session.scalars(query))

