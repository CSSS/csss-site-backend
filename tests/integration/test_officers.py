import asyncio

import load_test_db
import pytest
from database import SQLALCHEMY_TEST_DATABASE_URL, DatabaseSessionManager
from officers.constants import OfficerPosition
from officers.crud import current_executive_team, most_recent_exec_term


# TODO: run this again for every function?
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
        assert (await most_recent_exec_term(db_session, "blarg")) is None
        assert await most_recent_exec_term(db_session, "abc22") is None
        abc11_officer_term = await most_recent_exec_term(db_session, "abc11")

        assert abc11_officer_term.computing_id == "abc11"
        assert abc11_officer_term.position == OfficerPosition.ExecutiveAtLarge.value
        assert abc11_officer_term.start_date is not None
        assert abc11_officer_term.end_date is None
        assert abc11_officer_term.nickname == "the holy A"
        assert abc11_officer_term.favourite_course_0 == "CMPT 361"
        assert abc11_officer_term.biography == "Hi! I'm person A and I want school to be over ; _ ;"

        # TODO: fix current_executive_team function
        current_exec_team = await current_executive_team(db_session, include_private=False)
        assert current_exec_team is not None
        assert len(current_exec_team.keys()) == 1
        assert current_exec_team.keys()[0] == OfficerPosition.ExecutiveAtLarge.value
        assert current_exec_team.values()[0].favourite_course_0 == "CMPT 361"
        assert current_exec_team.values()[0].csss_email == OfficerPosition.VicePresident.to_email()
        assert current_exec_team.values()[0].private_data is None

        current_exec_team = await current_executive_team(db_session, include_private=True)
        assert current_exec_team is not None
        assert len(current_exec_team) == 1
        assert current_exec_team.keys()[0] == OfficerPosition.ExecutiveAtLarge.value
        assert current_exec_team.values()[0].favourite_course_0 == "CMPT 361"
        assert current_exec_team.values()[0].csss_email == OfficerPosition.ExecutiveAtLarge.to_email()
        assert current_exec_team.values()[0].private_data is not None
        assert current_exec_team.values()[0].computing_id == "abc11"

#async def test__update_execs(database_setup):
#    # TODO: the second time an update_officer_info call occurs, the user should be updated with info
#    pass
