# This script resets the test database, performs migrations, then loads test data into the db.
#
# python load_test_db.py

import asyncio
from datetime import UTC, date, datetime, timedelta

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

# NOTE: make sure you import from a file in your module which (at least) indirectly contains those
# tables, or the current python context will not be able to find them & they won't be loaded
from auth.crud import create_user_session, update_site_user
from database import SQLALCHEMY_TEST_DATABASE_URL, Base, DatabaseSessionManager
from elections.crud import create_election, update_election
from elections.tables import ElectionDB
from nominees.crud import create_nominee_info
from nominees.tables import NomineeInfoDB
from officers.constants import OfficerPositionEnum
from officers.crud import (
    create_new_officer_info,
    create_new_officer_term,
    update_officer_info,
    update_officer_term,
)
from officers.tables import OfficerInfoDB, OfficerTermDB
from registrations.crud import add_registration
from registrations.tables import NomineeApplicationDB


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
        # TODO: need to make sure that everything that would create a table is imported...
        # TODO: come up with a better solution - https://github.com/sqlalchemy/sqlalchemy/discussions/8650
        await connection.run_sync(Base.metadata.create_all)
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
    await update_site_user(db_session, "temp_id_314", "www.my_profile_picture_url.ca/test")
    await db_session.commit()


async def load_test_officers_data(db_session: AsyncSession):
    print("login the 3 users, putting them in the site users table")
    await create_user_session(db_session, "temp_id_1", "abc11")
    await create_user_session(db_session, "temp_id_2", "abc22")
    await create_user_session(db_session, "temp_id_3", "abc33")
    await db_session.commit()

    print("add officer info")
    # this person has uploaded all of their info
    await create_new_officer_info(
        db_session,
        OfficerInfoDB(
            legal_name="Person A",
            discord_id=str(88_1234_7182_4877_1111),
            discord_name="person_a_yeah",
            discord_nickname="aaa",
            computing_id="abc11",
            phone_number="1234567890",
            github_username="person_a",
            google_drive_email="person_a@gmail.com",
        ),
    )
    # this person has not joined the CSSS discord, so their discord name & nickname could not be found
    await create_new_officer_info(
        db_session,
        OfficerInfoDB(
            computing_id="abc22",
            legal_name="Person B",
            phone_number="1112223333",
            discord_id=str(88_1234_7182_4877_2222),
            discord_name=None,
            discord_nickname=None,
            google_drive_email="person_b@gmail.com",
            github_username="person_b",
        ),
    )
    # this person has uploaded the minimal amount of information
    await create_new_officer_info(
        db_session,
        OfficerInfoDB(
            legal_name="Person C",
            discord_id=None,
            discord_name=None,
            discord_nickname=None,
            computing_id="abc33",
            phone_number=None,
            github_username=None,
            google_drive_email=None,
        ),
    )
    await db_session.commit()

    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id="abc11",
            position=OfficerPositionEnum.VICE_PRESIDENT,
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() - timedelta(days=1),
            nickname="the A",
            favourite_course_0="CMPT 125",
            favourite_course_1="CA 149",
            favourite_pl_0="Turbo Pascal",
            favourite_pl_1="BASIC",
            biography="Hi! I'm person A and I do lots of cool things! :)",
            photo_url=None,  # TODO: this should be replaced with a default image
        ),
    )
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id="abc11",
            position=OfficerPositionEnum.EXECUTIVE_AT_LARGE,
            start_date=date.today(),
            end_date=None,
            nickname="the holy A",
            favourite_course_0="CMPT 361",
            favourite_course_1="MACM 316",
            favourite_pl_0="Turbo Pascal",
            favourite_pl_1="Rust",
            biography="Hi! I'm person A and I want school to be over ; _ ;",
            photo_url=None,  # TODO: this should be replaced with a default image
        ),
    )
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id="abc33",
            position=OfficerPositionEnum.PRESIDENT,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            nickname="CC",
            favourite_course_0="CMPT 999",
            favourite_course_1="CMPT 354",
            favourite_pl_0="C++",
            favourite_pl_1="C",
            biography="I'm person C...",
            photo_url=None,  # TODO: this should be replaced with a default image
        ),
    )
    # this officer term is not fully filled in
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id="abc22",
            position=OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            nickname="Bee",
            favourite_course_0="CMPT 604",
            favourite_course_1=None,
            favourite_pl_0="B",
            favourite_pl_1="N/A",
            biography=None,
            photo_url=None,  # TODO: this should be replaced with a default image
        ),
    )
    await db_session.commit()

    await update_officer_info(
        db_session,
        OfficerInfoDB(
            legal_name="Person C ----",
            discord_id=None,
            discord_name=None,
            discord_nickname=None,
            computing_id="abc33",
            # adds a phone number
            phone_number="123-456-7890",
            github_username=None,
            google_drive_email=None,
        ),
    )
    await update_officer_term(
        db_session,
        OfficerTermDB(
            computing_id="abc33",
            position=OfficerPositionEnum.PRESIDENT,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            nickname="SEE SEE",
            favourite_course_0="CMPT 999",
            favourite_course_1="CMPT 354",
            favourite_pl_0="C++",
            favourite_pl_1="C",
            biography="You see, I'm person C...",
            photo_url=None,
        ),
    )
    await db_session.commit()


SYSADMIN_COMPUTING_ID = "pkn4"


async def load_sysadmin(db_session: AsyncSession):
    # put your computing id here for testing purposes
    print(f"loading new sysadmin '{SYSADMIN_COMPUTING_ID}'")
    await create_user_session(db_session, f"temp_id_{SYSADMIN_COMPUTING_ID}", SYSADMIN_COMPUTING_ID)
    await create_new_officer_info(
        db_session,
        OfficerInfoDB(
            legal_name="Puneet North",
            discord_id=None,
            discord_name=None,
            discord_nickname=None,
            computing_id=SYSADMIN_COMPUTING_ID,
            phone_number=None,
            github_username=None,
            google_drive_email=None,
        ),
    )
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id=SYSADMIN_COMPUTING_ID,
            position=OfficerPositionEnum.FIRST_YEAR_REPRESENTATIVE,
            start_date=date.today() - timedelta(days=(365 * 3)),
            end_date=date.today() - timedelta(days=(365 * 2)),
            nickname="G1",
            favourite_course_0="MACM 101",
            favourite_course_1="CMPT 125",
            favourite_pl_0="C#",
            favourite_pl_1="C++",
            biography="o hey fellow kids \n\n\n I can newline",
            photo_url=None,
        ),
    )
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id=SYSADMIN_COMPUTING_ID,
            position=OfficerPositionEnum.SYSTEM_ADMINISTRATOR,
            start_date=date.today() - timedelta(days=365),
            end_date=None,
            nickname="G2",
            favourite_course_0="CMPT 379",
            favourite_course_1="CMPT 295",
            favourite_pl_0="Rust",
            favourite_pl_1="C",
            biography="The systems are good o7",
            photo_url=None,
        ),
    )
    # a future term
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id=SYSADMIN_COMPUTING_ID,
            position=OfficerPositionEnum.DIRECTOR_OF_ARCHIVES,
            start_date=date.today() + timedelta(days=365 * 1),
            end_date=date.today() + timedelta(days=365 * 2),
            nickname="G3",
            favourite_course_0="MACM 102",
            favourite_course_1="CMPT 127",
            favourite_pl_0="C%",
            favourite_pl_1="C$$",
            biography="o hey fellow kids \n\n\n I will can newline .... !!",
            photo_url=None,
        ),
    )
    await db_session.commit()


WEBMASTER_COMPUTING_ID = "jbriones"


async def load_webmaster(db_session: AsyncSession):
    # put your computing id here for testing purposes
    print(f"loading new webmaster '{WEBMASTER_COMPUTING_ID}'")
    await create_user_session(db_session, f"temp_id_{WEBMASTER_COMPUTING_ID}", WEBMASTER_COMPUTING_ID)
    await create_new_officer_info(
        db_session,
        OfficerInfoDB(
            legal_name="Jon Andre Briones",
            discord_id=None,
            discord_name=None,
            discord_nickname=None,
            computing_id=WEBMASTER_COMPUTING_ID,
            phone_number=None,
            github_username=None,
            google_drive_email=None,
        ),
    )
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id=WEBMASTER_COMPUTING_ID,
            position=OfficerPositionEnum.FIRST_YEAR_REPRESENTATIVE,
            start_date=date.today() - timedelta(days=(365 * 3)),
            end_date=date.today() - timedelta(days=(365 * 2)),
            nickname="Jon Andre Briones",
            favourite_course_0="CMPT 379",
            favourite_course_1="CMPT 371",
            favourite_pl_0="TypeScript",
            favourite_pl_1="C#",
            biography="o hey fellow kids \n\n\n I can newline",
            photo_url=None,
        ),
    )
    await create_new_officer_term(
        db_session,
        OfficerTermDB(
            computing_id=WEBMASTER_COMPUTING_ID,
            position=OfficerPositionEnum.WEBMASTER,
            start_date=date.today() - timedelta(days=365),
            end_date=None,
            nickname="G2",
            favourite_course_0="CMPT 379",
            favourite_course_1="CMPT 295",
            favourite_pl_0="Rust",
            favourite_pl_1="C",
            biography="The systems are good o7",
            photo_url=None,
        ),
    )
    await db_session.commit()


async def load_test_elections_data(db_session: AsyncSession):
    print("loading election data...")
    await create_election(
        db_session,
        ElectionDB(
            slug="test-election-1",
            name="test election    1",
            type="general_election",
            datetime_start_nominations=datetime.now(UTC) - timedelta(days=400),
            datetime_start_voting=datetime.now(UTC) - timedelta(days=395, hours=4),
            datetime_end_voting=datetime.now(UTC) - timedelta(days=390, hours=8),
            available_positions=["president", "vice-president"],
            survey_link="https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        ),
    )
    await update_election(
        db_session,
        ElectionDB(
            slug="test-election-1",
            name="test election    1",
            type="general_election",
            datetime_start_nominations=datetime.now(UTC) - timedelta(days=400),
            datetime_start_voting=datetime.now(UTC) - timedelta(days=395, hours=4),
            datetime_end_voting=datetime.now(UTC) - timedelta(days=390, hours=8),
            available_positions=["president", "vice-president", "treasurer"],
            survey_link="https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        ),
    )
    await create_election(
        db_session,
        ElectionDB(
            slug="test-election-2",
            name="test election 2",
            type="by_election",
            datetime_start_nominations=datetime.now(UTC) - timedelta(days=1),
            datetime_start_voting=datetime.now(UTC) + timedelta(days=7),
            datetime_end_voting=datetime.now(UTC) + timedelta(days=14),
            available_positions=["president", "vice-president", "treasurer"],
            survey_link="https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5 (oh yeah)",
        ),
    )
    await create_nominee_info(
        db_session,
        NomineeInfoDB(
            computing_id="jdo12",
            full_name="John Doe",
            linked_in="linkedin.com/john-doe",
            instagram="john_doe",
            email="john_doe@doe.com",
            discord_username="doedoe",
        ),
    )
    await create_nominee_info(
        db_session,
        NomineeInfoDB(
            computing_id="pkn4",
            full_name="Puneet North",
            linked_in="linkedin.com/john-doe3",
            instagram="john_doe 3",
            email="john_do3e@doe.com",
            discord_username="doedoe3",
        ),
    )
    await create_election(
        db_session,
        ElectionDB(
            slug="my-cr-election-3",
            name="my cr election 3",
            type="council_rep_election",
            datetime_start_nominations=datetime.now(UTC) - timedelta(days=5),
            datetime_start_voting=datetime.now(UTC) - timedelta(days=1, hours=4),
            datetime_end_voting=datetime.now(UTC) + timedelta(days=5, hours=8),
            available_positions=["president", "vice-president", "treasurer"],
            survey_link="https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        ),
    )
    await create_election(
        db_session,
        ElectionDB(
            slug="THE-SUPER-GENERAL-ELECTION-friends",
            name="THE SUPER GENERAL ELECTION & friends",
            type="general_election",
            datetime_start_nominations=datetime.now(UTC) + timedelta(days=5),
            datetime_start_voting=datetime.now(UTC) + timedelta(days=10, hours=4),
            datetime_end_voting=datetime.now(UTC) + timedelta(days=15, hours=8),
            available_positions=["president", "vice-president", "treasurer"],
            survey_link=None,
        ),
    )
    await db_session.commit()


async def load_test_election_nominee_application_data(db_session: AsyncSession):
    await add_registration(
        db_session,
        NomineeApplicationDB(
            computing_id=SYSADMIN_COMPUTING_ID,
            nominee_election="test-election-2",
            position="vice-president",
            speech=None,
        ),
    )
    await db_session.commit()


# ----------------------------------------------------------------- #


async def async_main(sessionmanager):
    await reset_db(sessionmanager._engine)
    async with sessionmanager.session() as db_session:
        await load_test_auth_data(db_session)
        await load_test_officers_data(db_session)
        await load_sysadmin(db_session)
        await load_webmaster(db_session)
        await load_test_elections_data(db_session)
        await load_test_election_nominee_application_data(db_session)


if __name__ == "__main__":
    response = input(f"This will reset the {SQLALCHEMY_TEST_DATABASE_URL} database, are you okay with this? (y/N): ")
    if response.lower() != "y":
        print("exiting without doing anything...")
        quit(0)

    print("Resetting DB...")
    sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": False})
    asyncio.run(async_main(sessionmanager))

    print("Done!")
