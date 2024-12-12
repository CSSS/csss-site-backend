import asyncio

import pytest

import load_test_db
from database import SQLALCHEMY_TEST_DATABASE_URL, DatabaseSessionManager
from officers.constants import OfficerPosition
from officers.crud import all_officers, current_officers, get_active_officer_terms

# TODO: setup a database on the CI machine & run this as a unit test then (since
# this isn't really an integration test)

# run this again for every function
@pytest.fixture(scope="function")
async def database_setup():
    # reset the database again, just in case
    print("Resetting DB...")
    sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": False}, check_db=False)
    await DatabaseSessionManager.test_connection(SQLALCHEMY_TEST_DATABASE_URL)
    await load_test_db.async_main(sessionmanager)
    print("Done setting up!")

    return sessionmanager

@pytest.mark.asyncio
async def test__read_execs(database_setup):
    sessionmanager = await database_setup
    async with sessionmanager.session() as db_session:
        # test that reads from the database succeeded as expected
        assert (await get_active_officer_terms(db_session, "blarg")) is None
        assert (await get_active_officer_terms(db_session, "abc22")) is None
        abc11_officer_terms = await get_active_officer_terms(db_session, "abc11")

        assert abc11_officer_terms[0].computing_id == "abc11"
        assert abc11_officer_terms[0].position == OfficerPosition.EXECUTIVE_AT_LARGE
        assert abc11_officer_terms[0].start_date is not None
        assert abc11_officer_terms[0].end_date is None
        assert abc11_officer_terms[0].nickname == "the holy A"
        assert abc11_officer_terms[0].favourite_course_0 == "CMPT 361"
        assert abc11_officer_terms[0].biography == "Hi! I'm person A and I want school to be over ; _ ;"

        current_exec_team = await current_officers(db_session, include_private=False)
        assert current_exec_team is not None
        assert len(current_exec_team.keys()) == 1
        assert next(iter(current_exec_team.keys())) == OfficerPosition.PRESIDENT
        assert next(iter(current_exec_team.values()))[0].favourite_course_0 == "CMPT 999"
        assert next(iter(current_exec_team.values()))[0].csss_email == OfficerPosition.President.to_email()
        assert next(iter(current_exec_team.values()))[0].private_data is None

        current_exec_team = await current_officers(db_session, include_private=True)
        assert current_exec_team is not None
        assert len(current_exec_team) == 1
        assert next(iter(current_exec_team.keys())) == OfficerPosition.PRESIDENT
        assert next(iter(current_exec_team.values()))[0].favourite_course_0 == "CMPT 999"
        assert next(iter(current_exec_team.values()))[0].csss_email == OfficerPosition.President.to_email()
        assert next(iter(current_exec_team.values()))[0].private_data is not None
        assert next(iter(current_exec_team.values()))[0].private_data.computing_id == "abc33"

        all_terms = await all_officers(db_session, include_private=True)
        assert len(all_terms) == 3


#async def test__update_execs(database_setup):
#    # TODO: the second time an update_officer_info call occurs, the user should be updated with info
#    pass
