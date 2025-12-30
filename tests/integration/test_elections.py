import asyncio
import datetime
from datetime import timedelta

import pytest
from httpx import AsyncClient

import load_test_db
from database import DBSession
from elections.crud import (
    get_all_elections,
    get_election,
)
from nominees.crud import (
    get_nominee_info,
)
from registrations.crud import (
    get_all_registrations_in_election,
)

TEST_ELECTION_2 = "test election 2"

pytestmark = pytest.mark.asyncio(loop_scope="session")


# database testing-------------------------------
async def test_read_elections(db_session: DBSession):
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
async def test__get_all_elections(client):
    response = await client.get("/election")
    assert response.status_code == 200
    assert response.json() != {}


async def test__get_single_election(client):
    # Returns private details when the time is allowed. If user is an admin or election officer, returns computing ids for each candidate as well.
    response = await client.get(f"/election/{TEST_ELECTION_2}")
    assert response.status_code == 200
    assert response.json() != {}
    # if candidates filled, enure unauthorized values remain hidden
    if "candidates" in response.json() and response.json()["candidates"]:
        for cand in response.json()["candidates"]:
            assert "computing_id" not in cand


async def test__get_single_registrations(client: AsyncClient):
    # ensure that registrations can be viewed
    # Only authorized users can access registrations get
    response = await client.get(f"/registration/{TEST_ELECTION_2}")
    assert response.status_code == 401

    response = await client.get("/nominee/pkn4")
    assert response.status_code == 401


async def test__create_election(client: AsyncClient):
    response = await client.post(
        "/election",
        json={
            "name": TEST_ELECTION_2,
            "type": "general_election",
            "datetime_start_nominations": "2025-08-18T09:00:00Z",
            "datetime_start_voting": "2025-09-03T09:00:00Z",
            "datetime_end_voting": "2025-09-18T23:59:59Z",
            "available_positions": ["president"],
            "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        },
    )
    assert response.status_code == 401  # unauthorized access to create an election


async def test__create_registration(client: AsyncClient):
    # ensure that registrations can be viewed
    response = await client.post(
        "/registration/{test-election-1}",
        json={
            "computing_id": "1234567",
            "position": "president",
        },
    )
    assert response.status_code == 401  # unauthorized access to register candidates


async def test__update_election(client: AsyncClient):
    response = await client.patch(
        f"/election/{TEST_ELECTION_2}",
        json={
            "type": "general_election",
            "datetime_start_nominations": "2025-08-18T09:00:00Z",
            "datetime_start_voting": "2025-09-03T09:00:00Z",
            "datetime_end_voting": "2025-09-18T23:59:59Z",
            "available_positions": ["president", "treasurer"],
            "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        },
    )
    assert response.status_code == 401


async def test__update_registration(client: AsyncClient):
    response = await client.patch(
        f"/registration/{TEST_ELECTION_2}/vice-president/{load_test_db.SYSADMIN_COMPUTING_ID}",
        json={
            "position": "president",
            "speech": "I would like to run for president because I'm the best in Valorant at SFU.",
        },
    )
    assert response.status_code == 401


async def test__update_nominee(client: AsyncClient):
    response = await client.patch(
        "/nominee/jdo12",
        json={
            "full_name": "John Doe VI",
            "linked_in": "linkedin.com/john-doe-vi",
            "instagram": "john_vi",
            "email": "johndoe_vi@doe.com",
            "discord_username": "johnyy",
        },
    )
    assert response.status_code == 401


async def test__delete_election(client: AsyncClient):
    response = await client.delete(f"/election/{TEST_ELECTION_2}")
    assert response.status_code == 401


async def test__delete_registration(client: AsyncClient):
    response = await client.delete(
        f"/registration/{TEST_ELECTION_2}/vice-president/{load_test_db.SYSADMIN_COMPUTING_ID}"
    )
    assert response.status_code == 401


# Admin API testing (with AUTH)-----------------------------------
async def test__admin_get_all_elections(admin_client: AsyncClient):
    # Login in as the website admin
    # session_id = "temp_id_" + load_test_db.SYSADMIN_COMPUTING_ID
    # async with database_setup.session() as db_session:
    #     await create_user_session(db_session, session_id, load_test_db.SYSADMIN_COMPUTING_ID)

    # client.cookies = {"session_id": session_id}

    # test that more info is given if logged in & with access to it
    response = await admin_client.get("/election")
    assert response.status_code == 200
    assert response.json() != {}


async def test__admin_get_single_election(admin_client: AsyncClient):
    # Returns private details when the time is allowed. If user is an admin or election officer, returns computing ids for each candidate as well.
    response = await admin_client.get(f"/election/{TEST_ELECTION_2}")
    assert response.status_code == 200
    assert response.json() != {}
    # if candidates filled, enure unauthorized values remain hidden
    if "candidates" in response.json() and response.json()["candidates"]:
        for cand in response.json()["candidates"]:
            assert "computing_id" in cand


async def test__admin_create_election(admin_client: AsyncClient):
    # ensure that authorized users can create an election
    response = await admin_client.post(
        "/election",
        json={
            "name": "testElection4",
            "type": "general_election",
            "datetime_start_nominations": (datetime.datetime.now(datetime.UTC) - timedelta(days=1)).isoformat(),
            "datetime_start_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=7)).isoformat(),
            "datetime_end_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=14)).isoformat(),
            "available_positions": ["president", "treasurer"],
            "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        },
    )
    assert response.status_code == 200
    # ensure that user can create election without knowing each position type
    response = await admin_client.post(
        "/election",
        json={
            "name": "byElection4",
            "type": "by_election",
            "datetime_start_nominations": (datetime.datetime.now(datetime.UTC) - timedelta(days=1)).isoformat(),
            "datetime_start_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=7)).isoformat(),
            "datetime_end_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=14)).isoformat(),
            "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        },
    )
    assert response.status_code == 200

    # ensure that registrations can be viewed
    # try to register for a past election -> should say nomination period expired
    testElection1 = "test election    1"
    response = await admin_client.post(
        f"/registration/{testElection1}",
        json={
            "computing_id": load_test_db.SYSADMIN_COMPUTING_ID,
            "position": "president",
        },
    )
    assert response.status_code == 400
    assert "nomination period" in response.json()["detail"]

    # ensure that registrations can be viewed
    # try to register for an invalid position will just throw a 422
    response = await admin_client.post(
        f"/registration/{TEST_ELECTION_2}",
        json={
            "computing_id": load_test_db.SYSADMIN_COMPUTING_ID,
            "position": "CEO",
        },
    )
    assert response.status_code == 422

    # ensure that registrations can be viewed
    # try to register in an unknown election
    response = await admin_client.post(
        "/registration/unknownElection12345",
        json={
            "computing_id": load_test_db.SYSADMIN_COMPUTING_ID,
            "position": "president",
        },
    )
    assert response.status_code == 404
    assert "does not exist" in response.json()["detail"]

    # ensure that registrations can be viewed
    # register for an election correctly
    response = await admin_client.post(
        f"/registration/{TEST_ELECTION_2}",
        json={
            "computing_id": "jdo12",
            "position": "president",
        },
    )
    assert response.status_code == 200


async def test__admin_get_registration(admin_client: AsyncClient):
    # ensure that registrations can be viewed
    # ensure that the above registration exists and is valid
    response = await admin_client.get(f"/registration/{TEST_ELECTION_2}")
    assert response.status_code == 200


async def test__admin_create_registration(admin_client: AsyncClient):
    # ensure that registrations can be viewed
    # duplicate registration
    response = await admin_client.post(
        f"/registration/{TEST_ELECTION_2}",
        json={
            "computing_id": "jdo12",
            "position": "president",
        },
    )
    assert response.status_code == 400
    assert "registered" in response.json()["detail"]


async def test__admin_update_election(admin_client: AsyncClient):
    # update the above election
    response = await admin_client.patch(
        "/election/testElection4",
        json={
            "election_type": "general_election",
            "datetime_start_nominations": (datetime.datetime.now(datetime.UTC) - timedelta(days=1)).isoformat(),
            "datetime_start_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=7)).isoformat(),
            "datetime_end_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=14)).isoformat(),
            "available_positions": ["president", "vice-president", "treasurer"],  # update this
            "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        },
    )
    assert response.status_code == 200


async def test__admin_update_registration(admin_client: AsyncClient):
    # ensure that registrations can be viewed
    # update the registration
    response = await admin_client.patch(
        f"/registration/{TEST_ELECTION_2}/vice-president/pkn4", json={"speech": "Vote for me as treasurer"}
    )
    assert response.status_code == 200

    # ensure that registrations can be viewed
    # try updating a non-registered election
    response = await admin_client.patch(
        "/registration/testElection4/pkn4",
        json={"position": "president", "speech": "Vote for me as president, I am good at valorant."},
    )
    assert response.status_code == 404


async def test__admin_delete_election(admin_client: AsyncClient):
    # delete an election
    response = await admin_client.delete("/election/testElection4")
    assert response.status_code == 200

    # TODO: Move these tests to a registrations test function
    # ensure that registrations can be viewed
    # delete a registration
    response = await admin_client.delete(f"/registration/{TEST_ELECTION_2}/president/jdo12")
    assert response.status_code == 200


async def test__admin_get_nominee(admin_client: AsyncClient):
    # get nominee info
    response = await admin_client.get(f"/nominee/{load_test_db.SYSADMIN_COMPUTING_ID}")
    assert response.status_code == 200


async def test__admin_update_nominee(admin_client: AsyncClient):
    # update nominee info
    response = await admin_client.patch(
        f"/nominee/{load_test_db.SYSADMIN_COMPUTING_ID}",
        json={
            "full_name": "Puneet N",
            "linked_in": "linkedin.com/not-my-linkedin",
        },
    )
    assert response.status_code == 200
