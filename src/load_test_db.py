# This script resets the test database, performs migrations, then loads test data into the db.
#
# python load_test_db.py

import asyncio
from datetime import datetime, timedelta

import sqlalchemy
from auth.crud import create_user_session
from database import SQLALCHEMY_TEST_DATABASE_URL, Base, DatabaseSessionManager
from officers.constants import OfficerPosition
from officers.crud import update_officer_info, update_officer_term
from officers.schemas import OfficerInfoData, OfficerTermData
from sqlalchemy.ext.asyncio import AsyncSession


async def reset_db(engine):
    # reset db
    async with engine.connect() as conn:
        table_list = await conn.run_sync(
            lambda sync_conn: sqlalchemy.inspect(sync_conn).get_table_names()
        )

    if len(table_list) != 0:
        print(f"found tables to delete: {table_list}")
        async with engine.connect() as connection:
            await connection.run_sync(Base.metadata.reflect)
            await connection.run_sync(Base.metadata.drop_all)
            await connection.commit()

    # check tables in db
    async with engine.connect() as conn:
        table_list = await conn.run_sync(
            lambda sync_conn: sqlalchemy.inspect(sync_conn).get_table_names()
        )
        if len(table_list) != 0:
            # TODO: replace this with logging
            print("FAILED TO REMOVE TABLES, THIS IS NOT GONNA BE FUN")
        else:
            print("deleted tables successfully")

    # fill with tables
    async with engine.connect() as connection:
        # TODO: need to make sure that everything that would create a table is imported...
        # TODO: come up with a better solution - https://github.com/sqlalchemy/sqlalchemy/discussions/8650
        await connection.run_sync(Base.metadata.create_all)
        await connection.commit()

    # check tables in db
    async with engine.connect() as conn:
        table_list = await conn.run_sync(
            lambda sync_conn: sqlalchemy.inspect(sync_conn).get_table_names()
        )
        if len(table_list) == 0:
            print("Uh oh, failed to create any tables...")
        else:
            print(f"new tables: {table_list}")

async def load_test_auth_data():
    pass

async def load_test_officers_data(db_session: AsyncSession):
    print("login the 3 users, putting them in the site users table")
    await create_user_session(db_session, "temp_id_1", "abc11")
    await create_user_session(db_session, "temp_id_2", "abc22")
    await create_user_session(db_session, "temp_id_3", "abc33")
    await db_session.commit()

    print("add officer info")
    # this person has uploaded all of their info
    update_officer_info(db_session, OfficerInfoData(
        legal_name="Person A",
        discord_id=str(88_1234_7182_4877_1111),
        discord_name="person_a_yeah",
        discord_nickname="aaa",

        computing_id="abc11",
        phone_number="1234567890",
        github_username="person_a",
        google_drive_email="person_a@gmail.com",
    ))
    # this person has not joined the CSSS discord, so their discord name & nickname could not be found
    update_officer_info(db_session, OfficerInfoData(
        legal_name="Person B",
        discord_id=str(88_1234_7182_4877_2222),
        discord_name=None,
        discord_nickname=None,

        computing_id="abc22",
        phone_number="1112223333",
        github_username="person_b",
        google_drive_email="person_b@gmail.com",
    ))
    # this person has uploaded the minimal amount of information
    update_officer_info(db_session, OfficerInfoData(
        legal_name="Person C",
        discord_id=None,
        discord_name=None,
        discord_nickname=None,

        computing_id="abc33",
        phone_number=None,
        github_username=None,
        google_drive_email=None,
    ))
    await db_session.commit()


    update_officer_term(db_session, OfficerTermData(
        computing_id="abc11",

        position=OfficerPosition.VicePresident.value,
        start_date=datetime.today() - timedelta(days=365),
        end_date=datetime.today() - timedelta(days=1),

        nickname="the A",
        favourite_course_0="CMPT 125",
        favourite_course_1="CA 149",

        favourite_pl_0="Turbo Pascal",
        favourite_pl_1="BASIC",

        biography="Hi! I'm person A and I do lots of cool things! :)",
        photo_url=None, # TODO: this should be replaced with a default image
    ))
    update_officer_term(db_session, OfficerTermData(
        computing_id="abc11",

        position=OfficerPosition.ExecutiveAtLarge.value,
        start_date=datetime.today(),
        end_date=None,

        nickname="the holy A",
        favourite_course_0="CMPT 361",
        favourite_course_1="MACM 316",

        favourite_pl_0="Turbo Pascal",
        favourite_pl_1="Rust",

        biography="Hi! I'm person A and I want school to be over ; _ ;",
        photo_url=None, # TODO: this should be replaced with a default image
    ))
    update_officer_term(db_session, OfficerTermData(
        computing_id="abc33",

        position=OfficerPosition.President.value,
        start_date=datetime.today(),
        end_date=datetime.today() + timedelta(days=365),

        nickname="CC",
        favourite_course_0="CMPT 999",
        favourite_course_1="CMPT 354",

        favourite_pl_0="C++",
        favourite_pl_1="C",

        biography="I'm person C...",
        photo_url=None, # TODO: this should be replaced with a default image
    ))
    await db_session.commit()

async def async_main(sessionmanager):
    await reset_db(sessionmanager._engine)
    async with sessionmanager.session() as db_session:
        # load_test_auth_data
        await load_test_officers_data(db_session)

if __name__ == "__main__":
    response = input(f"This will reset the {SQLALCHEMY_TEST_DATABASE_URL} database, are you okay with this? (y/N): ")
    if response.lower() != "y":
        print("exiting without doing anything...")
        quit(0)

    print("Resetting DB...")
    sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": False})
    asyncio.run(async_main(sessionmanager))

    print("Done!")
