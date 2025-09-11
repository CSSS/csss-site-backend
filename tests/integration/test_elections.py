import asyncio
from datetime import datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from src import load_test_db
from src.auth.crud import create_user_session
from src.database import SQLALCHEMY_TEST_DATABASE_URL, DatabaseSessionManager
from src.elections.crud import (
    # election crud
    get_all_elections,
    get_all_registrations_in_election,
    # election registration crud
    get_election,
    # info crud
    get_nominee_info,
)
from src.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

# creates HTTP test client for making requests
@pytest.fixture(scope="session")
async def client():
    # base_url is just a random placeholder url
    # ASGITransport is just telling the async client to pass all requests to app
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client

# run this again for every function
# sets up a clean database for each test function
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

# database testing-------------------------------
@pytest.mark.asyncio
async def test_read_elections(database_setup):
    sessionmanager = await database_setup
    async with sessionmanager.session() as db_session:
           # test that reads from the database succeeded as expected
           elections = await get_all_elections(db_session)
           assert elections is not None
           assert len(elections) > 0

           # False data test
           election_false = await get_election(db_session, "this-not-a-election")
           assert election_false is None


           # Test getting specific election
           election = await get_election(db_session, "test-election-1")
           assert election is not None
           assert election.slug == "test-election-1"
           assert election.name == "test election    1"
           assert election.type == "general_election"
           assert election.survey_link == "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5"

           # Test getting a specific registration
           registrations = await get_all_registrations_in_election(db_session, "test-election-1")
           assert registrations is not None

           # Test getting the nominee info
           nominee_info = await get_nominee_info(db_session, "jdo12")
           assert nominee_info is not None
           assert nominee_info.full_name == "John Doe"
           assert nominee_info.email == "john_doe@doe.com"
           assert nominee_info.discord_username == "doedoe"
           assert nominee_info.linked_in == "linkedin.com/john-doe"
           assert nominee_info.instagram == "john_doe"


# API endpoint testing (without AUTH)--------------------------------------
@pytest.mark.anyio
async def test_endpoints(client, database_setup):
    response = await client.get("/elections")
    assert response.status_code == 200
    assert response.json() != {}

    # Returns private details when the time is allowed. If user is an admin or elections officer, returns computing ids for each candidate as well.
    election_name = "test election 2"
    response = await client.get(f"/elections/{election_name}")
    assert response.status_code == 200
    assert response.json() != {}
    # if candidates filled, enure unauthorized values remain hidden
    if "candidates" in response.json() and response.json()["candidates"]:
        for cand in response.json()["candidates"]:
         assert "computing_id" not in cand

    # Only authorized users can access registrations get
    response = await client.get(f"/elections/registration/{election_name}")
    assert response.status_code == 401

    response = await client.get("/elections/nominee/pkn4")
    assert response.status_code == 401

    response = await client.post("/elections", json={
        "name": election_name,
        "type": "general_election",
        "datetime_start_nominations": "2025-08-18T09:00:00Z",
        "datetime_start_voting": "2025-09-03T09:00:00Z",
        "datetime_end_voting": "2025-09-18T23:59:59Z",
        "available_positions": ["president"],
        "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5"
    })
    assert response.status_code == 401 # unauthorized access to create an election

    response = await client.post("/elections/registration/{test-election-1}", json={
        "computing_id": "1234567",
        "position": "president",
    })
    assert response.status_code == 401 # unauthorized access to register candidates

    response = await client.patch(f"/elections/{election_name}", json={
        "type": "general_election",
        "datetime_start_nominations": "2025-08-18T09:00:00Z",
        "datetime_start_voting": "2025-09-03T09:00:00Z",
        "datetime_end_voting": "2025-09-18T23:59:59Z",
        "available_positions": ["president", "treasurer"],
        "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5"

    })
    assert response.status_code == 401

    response = await client.patch(f"/elections/registration/{election_name}/vice-president/{load_test_db.SYSADMIN_COMPUTING_ID}", json={
        "position": "president",
        "speech": "I would like to run for president because I'm the best in Valorant at SFU."
    })
    assert response.status_code == 401

    response = await client.patch("/elections/nominee/jdo12", json={
        "full_name": "John Doe VI",
        "linked_in": "linkedin.com/john-doe-vi",
        "instagram": "john_vi",
        "email": "johndoe_vi@doe.com",
        "discord_username": "johnyy"
    })
    assert response.status_code == 401

    response = await client.delete(f"/elections/{election_name}")
    assert response.status_code == 401

    response = await client.delete(f"/elections/registration/{election_name}/vice-president/{load_test_db.SYSADMIN_COMPUTING_ID}")
    assert response.status_code == 401


# Admin API testing (with AUTH)-----------------------------------
@pytest.mark.anyio
async def test_endpoints_admin(client, database_setup):
    # Login in as the website admin
    session_id = "temp_id_" + load_test_db.SYSADMIN_COMPUTING_ID
    async with database_setup.session() as db_session:
        await create_user_session(db_session, session_id, load_test_db.SYSADMIN_COMPUTING_ID)

    client.cookies = { "session_id": session_id }

    # test that more info is given if logged in & with access to it
    response = await client.get("/elections")
    assert response.status_code == 200
    assert response.json() != {}

    # Returns private details when the time is allowed. If user is an admin or elections officer, returns computing ids for each candidate as well.
    election_name = "test election 2"
    response = await client.get(f"/elections/{election_name}")
    assert response.status_code == 200
    assert response.json() != {}
    # if candidates filled, enure unauthorized values remain hidden
    if "candidates" in response.json() and response.json()["candidates"]:
        for cand in response.json()["candidates"]:
         assert "computing_id" in cand

    # ensure that registrations can be viewed
    response = await client.get(f"/elections/registration/{election_name}")
    assert response.status_code == 200

    # ensure that authorized users can create an election
    response = await client.post("/elections", json={
        "name": "testElection4",
        "type": "general_election",
        "datetime_start_nominations": (datetime.now() - timedelta(days=1)).isoformat(),
        "datetime_start_voting": (datetime.now() + timedelta(days=7)).isoformat(),
        "datetime_end_voting": (datetime.now() + timedelta(days=14)).isoformat(),
        "available_positions": ["president", "treasurer"],
        "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5"
    })
    assert response.status_code == 200
    # ensure that user can create elections without knowing each position type
    response = await client.post("/elections", json={
        "name": "byElection4",
        "type": "by_election",
        "datetime_start_nominations": (datetime.now() - timedelta(days=1)).isoformat(),
        "datetime_start_voting": (datetime.now() + timedelta(days=7)).isoformat(),
        "datetime_end_voting": (datetime.now() + timedelta(days=14)).isoformat(),
        "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5"
    })
    assert response.status_code == 200

    # try to register for a past election -> should say nomination period expired
    testElection1 = "test election    1"
    response = await client.post(f"/elections/registration/{testElection1}", json={
        "computing_id": load_test_db.SYSADMIN_COMPUTING_ID,
        "position": "president",
    })
    assert response.status_code == 400
    assert "nomination period" in response.json()["detail"]

    # try to register for an invalid position will just throw a 422
    response = await client.post(f"/elections/registration/{election_name}", json={
        "computing_id": load_test_db.SYSADMIN_COMPUTING_ID,
        "position": "CEO",
    })
    assert response.status_code == 422

    # try to register in an unknown election
    response = await client.post("/elections/registration/unknownElection12345", json={
        "computing_id": load_test_db.SYSADMIN_COMPUTING_ID,
        "position": "president",
    })
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]



    # register for an election correctly
    response = await client.post(f"/elections/registration/{election_name}", json={
        "computing_id": "jdo12",
        "position": "president",
    })
    assert response.status_code == 200
    # ensure that the above registration exists and is valid
    response = await client.get(f"/elections/registration/{election_name}")
    assert response.status_code == 200

    # duplicate registration
    response = await client.post(f"/elections/registration/{election_name}", json={
        "computing_id": "jdo12",
        "position": "president",
    })
    assert response.status_code == 400
    assert "registered" in response.json()["detail"]

    # update the above election
    response = await client.patch("/elections/testElection4", json={
        "election_type": "general_election",
        "datetime_start_nominations": (datetime.now() - timedelta(days=1)).isoformat(),
        "datetime_start_voting": (datetime.now() + timedelta(days=7)).isoformat(),
        "datetime_end_voting": (datetime.now() + timedelta(days=14)).isoformat(),
        "available_positions": ["president", "vice-president", "treasurer"],  # update this
        "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5"
    })
    assert response.status_code == 200

    # update the registration
    await client.patch(f"/elections/registration/{election_name}/vice-president/pkn4", json={
        "speech": "Vote for me as treasurer"
    })
    assert response.status_code == 200

    # try updating a non-registered election
    response = await client.patch("/elections/registration/testElection4/pkn4", json={
        "position": "president",
        "speech": "Vote for me as president, I am good at valorant."
    })
    assert response.status_code == 404

    # delete an election
    response = await client.delete("/elections/testElection4")
    assert response.status_code == 200

    # delete a registration
    response = await client.delete(f"/elections/registration/{election_name}/president/jdo12")
    assert response.status_code == 200

    # get nominee info
    response = await client.get(f"/elections/nominee/{load_test_db.SYSADMIN_COMPUTING_ID}")
    assert response.status_code == 200

    # update nominee info
    response = await client.patch(f"/elections/nominee/{load_test_db.SYSADMIN_COMPUTING_ID}", json={
        "full_name": "Puneet N",
        "linked_in": "linkedin.com/not-my-linkedin",
    })
    assert response.status_code == 200

    response = await client.get(f"/elections/nominee/{load_test_db.SYSADMIN_COMPUTING_ID}")
    assert response.status_code == 200
