from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

import database
from auth.constants import UserRole
from auth.tables import SiteUserDB, SiteUserRoleDB
from users.models import SiteUserCreate


def create_site_user(db_session: database.DBSession, user: SiteUserDB) -> None:
    db_session.add(user)


async def get_all_users(db_session: database.DBSession) -> Sequence[SiteUserDB]:
    query = select(SiteUserDB).options(selectinload(SiteUserDB.roles)).order_by(SiteUserDB.last_logged_in.desc())

    return (await db_session.scalars(query)).all()


def create_user_roles(db_session: database.DBSession, roles: list[SiteUserRoleDB]) -> None:
    db_session.add_all(roles)
