import asyncio  # NOTE: don't comment this out; it's required

import pytest
from httpx import ASGITransport, AsyncClient

import load_test_db
from auth.crud import create_user_session
from database import SQLALCHEMY_TEST_DATABASE_URL, DatabaseSessionManager
from main import app
from officers.constants import OfficerPosition
from officers.crud import all_officers, current_officers, get_active_officer_terms

# TODO: setup a database on the CI machine & run this as a unit test then (since
# this isn't really an integration test)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def client():
    # base_url is just a random placeholder url
    # ASGITransport is just telling the async client to pass all requests to app
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client

# run this again for every function
@pytest.fixture(scope="function")
async def database_setup():
    # reset the database again, just in case
    print("Resetting DB...")
    sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": False}, check_db=False)
    await DatabaseSessionManager.test_connection(SQLALCHEMY_TEST_DATABASE_URL)
    # this resets the contents of the database to be whatever is from `load_test_db.py`
    await load_test_db.async_main(sessionmanager)
    print("Done setting up!")

    return sessionmanager

# TODO: switch to mark.anyio
@pytest.mark.asyncio
async def test__read_execs(database_setup):
    sessionmanager = await database_setup
    async with sessionmanager.session() as db_session:
        # test that reads from the database succeeded as expected
        assert (await get_active_officer_terms(db_session, "blarg")) == []
        assert (await get_active_officer_terms(db_session, "abc22")) != []

        abc11_officer_terms = await get_active_officer_terms(db_session, "abc11")
        assert len(abc11_officer_terms) == 1
        assert abc11_officer_terms[0].computing_id == "abc11"
        assert abc11_officer_terms[0].position == OfficerPosition.EXECUTIVE_AT_LARGE
        assert abc11_officer_terms[0].start_date is not None
        assert abc11_officer_terms[0].nickname == "the holy A"
        assert abc11_officer_terms[0].favourite_course_0 == "CMPT 361"
        assert abc11_officer_terms[0].biography == "Hi! I'm person A and I want school to be over ; _ ;"

        current_exec_team = await current_officers(db_session, include_private=False)
        assert current_exec_team is not None
        assert len(current_exec_team.keys()) == 4
        assert next(iter(current_exec_team.keys())) == OfficerPosition.EXECUTIVE_AT_LARGE
        assert next(iter(current_exec_team.values()))[0].favourite_course_0 == "CMPT 361"
        assert next(iter(current_exec_team.values()))[0].csss_email == OfficerPosition.to_email(OfficerPosition.EXECUTIVE_AT_LARGE)
        assert next(iter(current_exec_team.values()))[0].private_data is None

        current_exec_team = await current_officers(db_session, include_private=True)
        assert current_exec_team is not None
        assert len(current_exec_team) == 4
        assert next(iter(current_exec_team.keys())) == OfficerPosition.EXECUTIVE_AT_LARGE
        assert next(iter(current_exec_team.values()))[0].favourite_course_0 == "CMPT 361"
        assert next(iter(current_exec_team.values()))[0].csss_email == OfficerPosition.to_email(OfficerPosition.EXECUTIVE_AT_LARGE)
        assert next(iter(current_exec_team.values()))[0].private_data is not None
        assert next(iter(current_exec_team.values()))[0].private_data.computing_id == "abc11"

        all_terms = await all_officers(db_session, include_private_data=True, include_future_terms=True)
        assert len(all_terms) == 6

#async def test__update_execs(database_setup):
#    # TODO: the second time an update_officer_info call occurs, the user should be updated with info
#    pass

@pytest.mark.anyio
async def test__endpoints(client, database_setup):
    # reset & load the test database

    response = await client.get("/officers/current")
    assert response.status_code == 200
    assert response.json() != {}
    assert len(response.json().values()) == 4
    assert not response.json()["executive at large"][0]["private_data"]

    response = await client.get("/officers/all?include_future_terms=false")
    assert response.status_code == 200
    assert response.json() != []
    assert len(response.json()) == 6
    assert not response.json()[0]["private_data"]

    response = await client.get("/officers/all?include_future_terms=true")
    assert response.status_code == 401

    """
    response = await client.get("/officers/all")
    assert response.status_code == 200
    assert response.json() != {}
    # TODO: ensure `include_future_terms` works

    # TODO: ensure the test database is being used & has access to abc11
    response = await client.get("/officers/terms/abc11")
    assert response.status_code == 200
    assert response.json() != {}
    """

@pytest.mark.anyio
async def test__endpoints_admin(client, database_setup):
    # login as website admin
    session_id = "temp_id_" + load_test_db.SYSADMIN_COMPUTING_ID
    async with database_setup.session() as db_session:
        await create_user_session(db_session, session_id, load_test_db.SYSADMIN_COMPUTING_ID)

    # test that more info is given if logged in & with access to it
    response = await client.get("/officers/current", cookies={ "session_id": session_id })
    assert response.status_code == 200
    assert response.json() != {}
    assert len(response.json().values()) == 4
    assert response.json()["executive at large"][0]["private_data"]

    response = await client.get("/officers/all?include_future_terms=true", cookies={ "session_id": session_id })
    assert response.status_code == 200
    assert response.json() != []
    print(len(response.json()))
    assert len(response.json()) == 6 # TODO: we expect larger than 6
    assert response.json()[0]["private_data"]["phone_number"] == "1234567890"

    # TODO: ensure that all endpoints are tested at least once
