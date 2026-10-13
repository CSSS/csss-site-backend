import datetime
from datetime import timedelta

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import create_user_session, get_site_user_by_computing_id
from auth.tables import SiteUserRoleDB
from candidates.crud import add_candidate, get_all_candidates_in_election
from candidates.tables import CandidateDB
from database import DBSession
from elections.crud import (
    create_election,
    get_all_elections,
    get_election,
)
from elections.models import ElectionTypeEnum
from elections.tables import ElectionDB
from nominees.crud import create_nominee_info, get_nominee_info
from nominees.tables import NomineeInfoDB
from utils.urls import slugify

TEST_ELECTION_1 = "integration-election-1"
TEST_ELECTION_2 = "integration election 2"
TEST_CANDIDATE_ID = "electnominee"
TEST_CANDIDATE_NAME = "Election Nominee"

pytestmark = pytest.mark.asyncio(loop_scope="session")

CANDIDATE_CONTACT_FIELDS = ["computing_id", "linked_in", "instagram", "email", "discord_username"]


def assert_public_candidate_fields(candidate: dict):
    for field in CANDIDATE_CONTACT_FIELDS:
        assert field not in candidate


def assert_private_candidate_fields(candidate: dict):
    for field in CANDIDATE_CONTACT_FIELDS:
        assert field in candidate


@pytest_asyncio.fixture(loop_scope="session")
async def admin_client(client: AsyncClient, db_session: DBSession):
    session_id = "election-admin-session"
    await create_user_session(db_session, session_id, "electadmin")
    user = await get_site_user_by_computing_id(db_session, "electadmin")
    assert user is not None
    db_session.add(SiteUserRoleDB(uid=user.uid, role=UserRole.ADMIN))
    await db_session.commit()
    client.cookies.set(COOKIE_SESSION_KEY, session_id, domain="test.local", path="/")
    yield client


@pytest_asyncio.fixture(loop_scope="session")
async def nominee_data(db_session: DBSession):
    for computing_id, full_name in [("jdo12", "John Doe"), (TEST_CANDIDATE_ID, TEST_CANDIDATE_NAME)]:
        await create_nominee_info(
            db_session,
            NomineeInfoDB(
                computing_id=computing_id,
                full_name=full_name,
                email="john_doe@doe.com",
                discord_username="doedoe",
                linked_in="linkedin.com/john-doe",
                instagram="john_doe",
            ),
        )
    await db_session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def election_data(db_session: DBSession, nominee_data):
    now = datetime.datetime.now(datetime.UTC)
    for slug, name in [(TEST_ELECTION_1, "test election    1"), (slugify(TEST_ELECTION_2), TEST_ELECTION_2)]:
        await create_election(
            db_session,
            ElectionDB(
                slug=slug,
                name=name,
                type=ElectionTypeEnum.GENERAL,
                datetime_start_nominations=now - timedelta(days=1),
                datetime_start_voting=now + timedelta(days=7),
                datetime_end_voting=now + timedelta(days=14),
                available_positions=["president", "vice-president", "treasurer"],
                survey_link="https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
            ),
        )
    await db_session.flush()
    await add_candidate(
        db_session,
        CandidateDB(
            computing_id=TEST_CANDIDATE_ID,
            nominee_election=slugify(TEST_ELECTION_2),
            position="vice-president",
            speech=None,
        ),
    )
    await db_session.commit()


# TODO: Split the candidate tests into their own file
# database testing-------------------------------
async def test_read_elections(db_session: DBSession, election_data):
    # test that reads from the database succeeded as expected
    elections = await get_all_elections(db_session)
    assert elections is not None
    assert {TEST_ELECTION_1, slugify(TEST_ELECTION_2)} <= {election.slug for election in elections}

    # False data test
    election_false = await get_election(db_session, "this-not-a-election")
    assert election_false is None

    # Test getting specific election
    election = await get_election(db_session, TEST_ELECTION_1)
    assert election is not None
    assert election.slug == TEST_ELECTION_1
    assert election.name == "test election    1"
    assert election.type == "general_election"
    assert election.survey_link == "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5"

    # Test getting a specific registration
    candidates = await get_all_candidates_in_election(db_session, TEST_ELECTION_1)
    assert candidates == []

    # Test getting the nominee info
    nominee_info = await get_nominee_info(db_session, "jdo12")
    assert nominee_info is not None
    assert nominee_info.full_name == "John Doe"
    assert nominee_info.email == "john_doe@doe.com"
    assert nominee_info.discord_username == "doedoe"
    assert nominee_info.linked_in == "linkedin.com/john-doe"
    assert nominee_info.instagram == "john_doe"


# API endpoint testing (without AUTH)--------------------------------------
async def test__get_all_elections(client: AsyncClient, election_data):
    response = await client.get("/api/election")
    assert response.status_code == 200
    assert slugify(TEST_ELECTION_2) in {election["slug"] for election in response.json()}
    for election in response.json():
        assert "candidates" not in election


async def test__get_all_elections_with_nominees_true(client: AsyncClient):
    response = await client.get("/api/election", params={"with_nominees": "true"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Must be an election officer to view nominees"}


async def test__get_single_election(client: AsyncClient, election_data):
    # Returns private details when the time is allowed. If user is an admin or election officer, returns computing ids for each candidate as well.
    response = await client.get(f"/api/election/{TEST_ELECTION_2}")
    assert response.status_code == 200
    assert response.json() != {}
    assert "candidates" not in response.json()
    assert "survey_link" not in response.json()


async def test__get_single_election_with_nominees_true(client: AsyncClient, election_data):
    response = await client.get(f"/api/election/{TEST_ELECTION_2}", params={"with_nominees": "true"})
    assert response.status_code == 200
    election_2_response = response.json()
    assert election_2_response != {}
    assert "candidates" in election_2_response
    assert "survey_link" not in election_2_response
    assert len(election_2_response["candidates"]) == 1
    for candidate in election_2_response["candidates"]:
        assert_public_candidate_fields(candidate)


async def test__get_single_candidates(client: AsyncClient):
    # ensure that candidates can be viewed
    # Only authorized users can access candidates get
    response = await client.get(f"/api/candidate/{TEST_ELECTION_2}")
    assert response.status_code == 401

    response = await client.get(f"/api/nominee/{TEST_CANDIDATE_ID}")
    assert response.status_code == 401


async def test__create_election(client: AsyncClient):
    response = await client.post(
        "/api/election",
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


async def test__create_candidate(client: AsyncClient):
    # ensure that candidates can be viewed
    response = await client.post(
        f"/api/candidate/{TEST_ELECTION_1}",
        json={
            "computing_id": "1234567",
            "position": "president",
        },
    )
    assert response.status_code == 401  # unauthorized access to register candidates


async def test__update_election(client: AsyncClient):
    response = await client.patch(
        f"/api/election/{TEST_ELECTION_2}",
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


async def test__update_candidate(client: AsyncClient):
    response = await client.patch(
        f"/api/candidate/{TEST_ELECTION_2}/vice-president/{TEST_CANDIDATE_ID}",
        json={
            "position": "president",
            "speech": "I would like to run for president because I'm the best in Valorant at SFU.",
        },
    )
    assert response.status_code == 401


async def test__update_nominee(client: AsyncClient):
    response = await client.patch(
        "/api/nominee/jdo12",
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
    response = await client.delete(f"/api/election/{TEST_ELECTION_2}")
    assert response.status_code == 401


async def test__delete_candidate(client: AsyncClient):
    response = await client.delete(f"/api/candidate/{TEST_ELECTION_2}/vice-president/{TEST_CANDIDATE_ID}")
    assert response.status_code == 401


# Admin API testing (with AUTH)-----------------------------------
async def test__admin_get_all_elections(admin_client: AsyncClient, election_data):
    response = await admin_client.get("/api/election")
    assert response.status_code == 200
    assert slugify(TEST_ELECTION_2) in {election["slug"] for election in response.json()}
    for election in response.json():
        assert "candidates" not in election


async def test__admin_get_all_elections_with_nominees_true(admin_client: AsyncClient, election_data):
    # Test on election 2, because it has candidates
    response = await admin_client.get("/api/election", params={"with_nominees": "true"})
    assert response.status_code == 200
    elections_list = {election["slug"]: election for election in response.json()}
    election_2_response = elections_list[slugify(TEST_ELECTION_2)]
    assert "survey_link" in election_2_response
    assert "candidates" in election_2_response
    assert len(election_2_response["candidates"]) == 1
    for candidate in election_2_response["candidates"]:
        assert_private_candidate_fields(candidate)


async def test__admin_get_single_election(admin_client: AsyncClient, election_data):
    # Returns private details when the time is allowed. If user is an admin or election officer, returns computing ids for each candidate as well.
    response = await admin_client.get(f"/api/election/{TEST_ELECTION_2}")
    assert response.status_code == 200
    assert response.json() != {}
    assert "candidates" not in response.json()
    assert "survey_link" in response.json()


async def test__admin_get_single_election_with_nominees_true(admin_client: AsyncClient, election_data):
    response = await admin_client.get(f"/api/election/{TEST_ELECTION_2}", params={"with_nominees": "true"})
    assert response.status_code == 200
    election_2_response = response.json()
    assert election_2_response != {}
    assert "survey_link" in election_2_response
    assert "candidates" in election_2_response
    assert len(election_2_response["candidates"]) == 1
    for candidate in election_2_response["candidates"]:
        assert_private_candidate_fields(candidate)


async def test__admin_create_election(db_session: DBSession, admin_client: AsyncClient):
    # ensure that authorized users can create an election
    response = await admin_client.post(
        "/api/election",
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
        "/api/election",
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


async def test__admin_get_candidate(admin_client: AsyncClient, election_data):
    # ensure that candidates can be viewed
    # ensure that the above candidate exists and is valid
    response = await admin_client.get(f"/api/candidate/{TEST_ELECTION_2}")
    assert response.status_code == 200
    assert response.json() == [
        {
            "computing_id": TEST_CANDIDATE_ID,
            "nominee_election": slugify(TEST_ELECTION_2),
            "position": "vice-president",
            "speech": None,
        }
    ]


async def test__admin_create_candidate(admin_client: AsyncClient, election_data):
    response = await admin_client.post(
        f"/api/candidate/{slugify(TEST_ELECTION_2)}",
        json={"computing_id": "jdo12", "position": "president"},
    )
    assert response.status_code == 200
    assert response.json()["speech"] is None


async def test__admin_update_election(db_session: DBSession, admin_client: AsyncClient):
    await create_election(
        db_session,
        ElectionDB(
            slug=slugify("testElection4"),
            name="testElection4",
            type=ElectionTypeEnum.GENERAL,
            datetime_start_nominations=datetime.datetime.now(datetime.UTC) - timedelta(days=1),
            datetime_start_voting=datetime.datetime.now(datetime.UTC) + timedelta(days=7),
            datetime_end_voting=datetime.datetime.now(datetime.UTC) + timedelta(days=14),
            available_positions=["president", "treasurer"],
            survey_link="https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        ),
    )
    await db_session.commit()
    # update the above election
    response = await admin_client.patch(
        "/api/election/testElection4",
        json={
            "type": "general_election",
            "datetime_start_nominations": (datetime.datetime.now(datetime.UTC) - timedelta(days=1)).isoformat(),
            "datetime_start_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=7)).isoformat(),
            "datetime_end_voting": (datetime.datetime.now(datetime.UTC) + timedelta(days=14)).isoformat(),
            "available_positions": ["president", "vice-president", "treasurer"],  # update this
            "survey_link": "https://youtu.be/dQw4w9WgXcQ?si=kZROi2tu-43MXPM5",
        },
    )
    assert response.status_code == 200
    assert response.json()["available_positions"] == ["president", "vice-president", "treasurer"]
    db_session.expire_all()
    updated = await get_election(db_session, slugify("testElection4"))
    assert updated is not None
    assert updated.available_positions == ["president", "vice-president", "treasurer"]


async def test__admin_update_candidate(admin_client: AsyncClient, election_data):
    # ensure that candidates can be viewed
    # update the candidate
    response = await admin_client.patch(
        f"/api/candidate/{TEST_ELECTION_2}/vice-president/{TEST_CANDIDATE_ID}",
        json={"speech": "Vote for me as treasurer"},
    )
    assert response.status_code == 200

    assert response.json()["speech"] == "Vote for me as treasurer"

    # try updating a non-registered election
    response = await admin_client.patch(
        f"/api/candidate/missing-election/president/{TEST_CANDIDATE_ID}",
        json={"position": "president", "speech": "Vote for me as president, I am good at valorant."},
    )
    assert response.status_code == 404


async def test__admin_delete_election(db_session: DBSession, admin_client: AsyncClient, election_data):
    response = await admin_client.delete(f"/api/candidate/{TEST_ELECTION_2}/vice-president/{TEST_CANDIDATE_ID}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert await get_all_candidates_in_election(db_session, slugify(TEST_ELECTION_2)) == []

    response = await admin_client.delete(f"/api/election/{TEST_ELECTION_2}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert await get_election(db_session, slugify(TEST_ELECTION_2)) is None


async def test__admin_get_nominee(admin_client: AsyncClient, nominee_data):
    # get nominee info
    response = await admin_client.get(f"/api/nominee/{TEST_CANDIDATE_ID}")
    assert response.status_code == 200
    assert response.json()["computing_id"] == TEST_CANDIDATE_ID
    assert response.json()["full_name"] == TEST_CANDIDATE_NAME


async def test__admin_update_nominee(admin_client: AsyncClient, nominee_data):
    # update nominee info
    response = await admin_client.patch(
        f"/api/nominee/{TEST_CANDIDATE_ID}",
        json={
            "full_name": "Updated Nominee",
            "linked_in": "linkedin.com/not-my-linkedin",
        },
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Nominee"
    assert response.json()["linked_in"] == "linkedin.com/not-my-linkedin"
