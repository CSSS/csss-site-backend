from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

import database
from auth.constants import UserRole
from auth.tables import SiteUserDB, SiteUserRoleDB


def create_site_user(db_session: database.DBSession, user: SiteUserDB) -> None:
    db_session.add(user)


async def get_all_users(db_session: database.DBSession) -> Sequence[SiteUserDB]:
    query = select(SiteUserDB).options(selectinload(SiteUserDB.roles)).order_by(SiteUserDB.last_logged_in.desc())

    return (await db_session.scalars(query)).all()


def create_user_roles(db_session: database.DBSession, roles: list[SiteUserRoleDB]) -> None:
    db_session.add_all(roles)


async def get_user_for_role_update(db_session: database.DBSession, computing_id: str) -> SiteUserDB | None:
    query = (
        select(SiteUserDB)
        .where(SiteUserDB.computing_id == computing_id)
        .options(selectinload(SiteUserDB.roles))
        .with_for_update()
    )
    user = await db_session.scalar(query)

    return user


async def delete_user_roles(db_session: database.DBSession, computing_id: str, roles_to_remove: set[UserRole]) -> None:
    query = (
        delete(SiteUserRoleDB)
        .where(SiteUserRoleDB.computing_id == computing_id, SiteUserRoleDB.role.in_(roles_to_remove))
        .execution_options(synchronize_session="fetch")
    )

    await db_session.execute(query)


async def delete_user(db_session: database.DBSession, computing_id: str) -> None:
    query = delete(SiteUserDB).where(SiteUserDB.computing_id == computing_id)

    await db_session.execute(query)
