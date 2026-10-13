# This script resets the test database, performs migrations, then loads test data into the db.
#
# python load_test_db.py

import asyncio
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import sqlalchemy
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import AsyncSession

import honorary.tables

# NOTE: make sure you import from a file in your module which (at least) indirectly contains those
# tables, or the current python context will not be able to find them & they won't be loaded
from auth.crud import create_user_session, get_site_user_by_computing_id
from auth.tables import AuthRedirectDB, SiteUserDB, SiteUserRoleDB, UserSessionDB
from candidates.crud import add_candidate
from candidates.tables import CandidateDB
from database import SQLALCHEMY_TEST_DATABASE_URL, Base, DatabaseSessionManager
from elections.crud import create_election, update_election
from elections.tables import ElectionDB
from image_asset.tables import ImageAssetDB
from nominees.crud import create_nominee_info
from nominees.tables import NomineeInfoDB
from officers.tables import OfficerInfoDB, OfficerTermDB
from translink.tables import TransLinkStaticScheduleDB
from users.crud import UserRole, create_site_user, create_user_roles


async def reset_db(engine):
    # reset db
    async with engine.connect() as conn:
        table_list = await conn.run_sync(lambda sync_conn: sqlalchemy.inspect(sync_conn).get_table_names())

    if len(table_list) != 0:
        print(f"found tables to delete: {table_list}")
        async with engine.connect() as connection:
            await connection.run_sync(Base.metadata.reflect)
            await connection.run_sync(Base.metadata.drop_all)
            await connection.commit()

    # check tables in db
    async with engine.connect() as conn:
        table_list = await conn.run_sync(lambda sync_conn: sqlalchemy.inspect(sync_conn).get_table_names())
        if len(table_list) != 0:
            # TODO: replace this with logging
            print("FAILED TO REMOVE TABLES, THIS IS NOT GONNA BE FUN")
        else:
            print("deleted tables successfully")

    # fill with tables
    async with engine.connect() as connection:

        def migrate(sync_connection: sqlalchemy.Connection):
            # Use the real schema, including officer triggers absent from ORM metadata.
            scripts = ScriptDirectory(str(Path(__file__).resolve().parent / "alembic"))
            with Operations.context(MigrationContext.configure(sync_connection)):
                for revision in reversed(list(scripts.walk_revisions())):
                    revision.module.upgrade()

        await connection.run_sync(migrate)
        await connection.commit()

    # check tables in db
    async with engine.connect() as conn:
        table_list = await conn.run_sync(lambda sync_conn: sqlalchemy.inspect(sync_conn).get_table_names())
        if len(table_list) == 0:
            print("Uh oh, failed to create any tables...")
        else:
            print(f"new tables: {table_list}")


# ----------------------------------------------------------------- #
# load db with test data


async def load_test_auth_data(db_session: AsyncSession):
    await create_user_session(db_session, "temp_id_314", "abc314")
    await db_session.commit()


SYSADMIN_COMPUTING_ID = "sysadmin"
SYSADMIN_FULL_NAME = "System Administrator"


async def load_sysadmin(db_session: AsyncSession):
    # put your computing id here for testing purposes
    print(f"loading new sysadmin '{SYSADMIN_COMPUTING_ID}'")
    await create_user_session(db_session, f"temp_id_{SYSADMIN_COMPUTING_ID}", SYSADMIN_COMPUTING_ID)
    sysadmin = await get_site_user_by_computing_id(db_session, SYSADMIN_COMPUTING_ID)
    assert sysadmin is not None
    user_roles = [
        SiteUserRoleDB(
            uid=sysadmin.uid,
            role=UserRole.ACCESS,
            added_by=sysadmin.uid,
            created_at=datetime.now(UTC),
        )
    ]
    create_user_roles(db_session, user_roles)
    await db_session.commit()


# ----------------------------------------------------------------- #


async def async_main(sessionmanager):
    await reset_db(sessionmanager._engine)
    async with sessionmanager.session() as db_session:
        await load_test_auth_data(db_session)
        await load_sysadmin(db_session)


if __name__ == "__main__":
    response = input(f"This will reset the {SQLALCHEMY_TEST_DATABASE_URL} database, are you okay with this? (y/N): ")
    if response.lower() != "y":
        print("exiting without doing anything...")
        quit(0)

    print("Resetting DB...")
    sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": False})
    asyncio.run(async_main(sessionmanager))

    print("Done!")
