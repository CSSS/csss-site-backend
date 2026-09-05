from collections.abc import Sequence

from sqlalchemy import select

import database
from auth.tables import SiteUserDB


async def get_all_users(db_session: database.DBSession) -> Sequence[SiteUserDB]:
    query = select(SiteUserDB).order_by(SiteUserDB.last_logged_in.desc())

    return (await db_session.scalars(query)).all()
