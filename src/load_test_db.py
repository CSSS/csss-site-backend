# This script resets the test database, performs migrations, then loads test data into the db.
#
# python load_test_db.py

import asyncio
from datetime import date, datetime, timedelta

import sqlalchemy
from auth.crud import create_user_session
from database import SQLALCHEMY_TEST_DATABASE_URL, Base, DatabaseSessionManager
from officers.constants import OfficerPosition
from officers.crud import create_new_officer_info, create_new_officer_term, update_officer_info, update_officer_term
from officers.tables import OfficerInfo, OfficerTerm
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
    await create_new_officer_info(db_session, OfficerInfo(
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
    await create_new_officer_info(db_session, OfficerInfo(
        computing_id="abc22",

        legal_name="Person B",
        phone_number="1112223333",

        discord_id=str(88_1234_7182_4877_2222),
        discord_name=None,
        discord_nickname=None,

        google_drive_email="person_b@gmail.com",
        github_username="person_b",
    ))
    # this person has uploaded the minimal amount of information
    await create_new_officer_info(db_session, OfficerInfo(
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

    await create_new_officer_term(db_session, OfficerTerm(
        computing_id="abc11",

        position=OfficerPosition.VICE_PRESIDENT,
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() - timedelta(days=1),

        nickname="the A",
        favourite_course_0="CMPT 125",
        favourite_course_1="CA 149",

        favourite_pl_0="Turbo Pascal",
        favourite_pl_1="BASIC",

        biography="Hi! I'm person A and I do lots of cool things! :)",
        photo_url=None, # TODO: this should be replaced with a default image
    ))
    await create_new_officer_term(db_session, OfficerTerm(
        computing_id="abc11",

        position=OfficerPosition.EXECUTIVE_AT_LARGE,
        start_date=date.today(),
        end_date=None,

        nickname="the holy A",
        favourite_course_0="CMPT 361",
        favourite_course_1="MACM 316",

        favourite_pl_0="Turbo Pascal",
        favourite_pl_1="Rust",

        biography="Hi! I'm person A and I want school to be over ; _ ;",
        photo_url=None, # TODO: this should be replaced with a default image
    ))
    await create_new_officer_term(db_session, OfficerTerm(
        computing_id="abc33",

        position=OfficerPosition.PRESIDENT,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),

        nickname="CC",
        favourite_course_0="CMPT 999",
        favourite_course_1="CMPT 354",

        favourite_pl_0="C++",
        favourite_pl_1="C",

        biography="I'm person C...",
        photo_url=None, # TODO: this should be replaced with a default image
    ))
    # this officer term is not fully filled in
    await create_new_officer_term(db_session, OfficerTerm(
        computing_id="abc22",

        position=OfficerPosition.DIRECTOR_OF_ARCHIVES,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),

        nickname="Bee",
        favourite_course_0="CMPT 604",
        favourite_course_1=None,

        favourite_pl_0="B",
        favourite_pl_1="N/A",

        biography=None,
        photo_url=None, # TODO: this should be replaced with a default image
    ))
    await db_session.commit()

    await update_officer_info(db_session, OfficerInfo(
        legal_name="Person C ----",
        discord_id=None,
        discord_name=None,
        discord_nickname=None,

        computing_id="abc33",
        # adds a phone number
        phone_number="123-456-7890",
        github_username=None,
        google_drive_email=None,
    ))
    await update_officer_term(db_session, OfficerTerm(
        computing_id="abc33",

        position=OfficerPosition.PRESIDENT,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),

        nickname="SEE SEE",
        favourite_course_0="CMPT 999",
        favourite_course_1="CMPT 354",

        favourite_pl_0="C++",
        favourite_pl_1="C",

        biography="You see, I'm person C...",
        photo_url=None,
    ))
    await db_session.commit()

async def load_sysadmin(db_session: AsyncSession):
    # put your computing id here for testing purposes
    SYSADMIN_COMPUTING_ID = "gsa92"

    print("loading new sysadmin")

    await create_user_session(db_session, f"temp_id_{SYSADMIN_COMPUTING_ID}", SYSADMIN_COMPUTING_ID)
    await create_new_officer_info(db_session, OfficerInfo(
        legal_name="Gabe Schulz",
        discord_id=None,
        discord_name=None,
        discord_nickname=None,

        computing_id=SYSADMIN_COMPUTING_ID,
        phone_number=None,
        github_username=None,
        google_drive_email=None,
    ))
    await create_new_officer_term(db_session, OfficerTerm(
        computing_id=SYSADMIN_COMPUTING_ID,

        position=OfficerPosition.SYSTEM_ADMINISTRATOR,
        start_date=date.today() - timedelta(days=365),
        end_date=None,

        nickname="Gabe",
        favourite_course_0="CMPT 379",
        favourite_course_1="CMPT 295",

        favourite_pl_0="Rust",
        favourite_pl_1="C",

        biography="The systems are good o7",
        photo_url=None,
    ))
    await create_new_officer_term(db_session, OfficerTerm(
        computing_id=SYSADMIN_COMPUTING_ID,

        position=OfficerPosition.FIRST_YEAR_REPRESENTATIVE,
        start_date=date.today() - timedelta(days=(365*3)),
        end_date=date.today() - timedelta(days=(365*2)),

        nickname="Gabe",
        favourite_course_0="MACM 101",
        favourite_course_1="CMPT 125",

        favourite_pl_0="C#",
        favourite_pl_1="C++",

        biography="o hey fellow kids \n\n\n I can newline",
        photo_url=None,
    ))
    await db_session.commit()

async def async_main(sessionmanager):
    await reset_db(sessionmanager._engine)
    async with sessionmanager.session() as db_session:
        # load_test_auth_data
        await load_test_officers_data(db_session)
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
