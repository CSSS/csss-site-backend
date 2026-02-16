import json
from datetime import date, timedelta

import pytest
from fastapi import status
from httpx import AsyncClient

import load_test_db
from database import DBSession
from officers.constants import OfficerPositionEnum
from officers.crud import current_officers, get_active_officer_terms, get_all_officers

# TODO: setup a database on the CI machine & run this as a unit test then (since
# this isn't really an integration test)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test__read_execs(db_session: DBSession):
    # test that reads from the database succeeded as expected
    assert (await get_active_officer_terms(db_session, "blarg")) == []
    assert (await get_active_officer_terms(db_session, "abc22")) != []

    abc11_officer_terms = await get_active_officer_terms(db_session, "abc11")
    assert len(abc11_officer_terms) == 2
    assert abc11_officer_terms[0].computing_id == "abc11"
    assert abc11_officer_terms[0].position == OfficerPositionEnum.EXECUTIVE_AT_LARGE
    assert abc11_officer_terms[0].start_date is not None
    assert abc11_officer_terms[0].nickname == "the holy A"
    assert abc11_officer_terms[0].favourite_course_0 == "CMPT 361"
    assert abc11_officer_terms[0].biography == "Hi! I'm person A and I want school to be over ; _ ;"

    current_exec_team = await current_officers(db_session)
    assert current_exec_team is not None
    assert len(current_exec_team) == 6
    # assert next(iter(current_exec_team)) == OfficerPositionEnum.EXECUTIVE_AT_LARGE
    # assert next(iter(current_exec_team))["favourite_course_0"] == "CMPT 361"
    # assert next(iter(current_exec_team.values()))[0].csss_email == OfficerPosition.to_email(OfficerPositionEnum.EXECUTIVE_AT_LARGE)
    # assert next(iter(current_exec_team.values()))[0].private_data is None

    all_terms = await get_all_officers(db_session, False, False)
    assert len(all_terms) == 8


# async def test__update_execs(database_setup):
#    # TODO: the second time an update_officer_info call occurs, the user should be updated with info
#    pass


async def test__get_officers(client: AsyncClient):
    # private data shouldn't be leaked
    response = await client.get("/officers/current")
    assert response.status_code == 200
    officers = response.json()
    assert len(officers) == 6
    officer = next(o for o in officers if o["position"] == OfficerPositionEnum.EXECUTIVE_AT_LARGE)
    assert "computing_id" not in officer
    assert "discord_id" not in officer
    assert "discord_name" not in officer
    assert "discord_nickname" not in officer
    assert "phone_number" not in officer
    assert "github_username" not in officer
    assert "google_drive_email" not in officer
    assert "photo_url" not in officer

    response = await client.get("/officers/all?include_future_terms=false")
    assert response.status_code == 200
    assert response.json() != []
    assert len(response.json()) == 8
    assert "computing_id" not in response.json()[0]
    assert "discord_id" not in response.json()[0]
    assert "discord_name" not in response.json()[0]
    assert "discord_nickname" not in response.json()[0]
    assert "phone_number" not in response.json()[0]
    assert "github_username" not in response.json()[0]
    assert "google_drive_email" not in response.json()[0]
    assert "photo_url" not in response.json()[0]

    response = await client.get("/officers/all?include_future_terms=true")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__get_officer_terms(client: AsyncClient):
    response = await client.get(f"/officers/terms/{load_test_db.SYSADMIN_COMPUTING_ID}?include_future_terms=false")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["nickname"] == "G2"
    assert response.json()[1]["nickname"] == "G1"

    response = await client.get("/officers/terms/balargho?include_future_terms=false")
    assert response.status_code == 200
    assert len(response.json()) == 0

    response = await client.get("/officers/terms/abc11?include_future_terms=true")
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = await client.get("/officers/info/abc11")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    response = await client.get(f"/officers/info/{load_test_db.SYSADMIN_COMPUTING_ID}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__user_create_officer_term(client: AsyncClient):
    response = await client.post(
        "officers/term",
        json=[
            {
                "computing_id": "ehbc12",
                "position": OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA,
                "start_date": "2025-12-29",
                "legal_name": "Eh Bc",
            }
        ],
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__create_officer_term_bad_enum(client: AsyncClient):
    # Position must be one of the enum positions
    response = await client.post(
        "officers/term",
        json=[{"computing_id": "ehbc12", "position": "balargho", "start_date": "2025-12-29", "legal_name": "Eh Bc"}],
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__update_officer_term(client: AsyncClient):
    # Only admins can update new terms
    response = await client.patch(
        "officers/info/abc11",
        json={
            "legal_name": "fancy name",
            "phone_number": None,
            "discord_name": None,
            "github_username": None,
            "google_drive_email": None,
        },
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

    response = await client.patch(
        "officers/term/1",
        content=json.dumps(
            {
                "computing_id": "abc11",
                "position": OfficerPositionEnum.VICE_PRESIDENT,
                "start_date": (date.today() - timedelta(days=365)).isoformat(),
                "end_date": (date.today() - timedelta(days=1)).isoformat(),
                # officer should change:
                "nickname": "1",
                "favourite_course_0": "2",
                "favourite_course_1": "3",
                "favourite_pl_0": "4",
                "favourite_pl_1": "5",
                "biography": "hello",
            }
        ),
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = await client.delete("officers/term/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__get_current_officers_admin(admin_client: AsyncClient):
    # test that more info is given if logged in & with access to it
    response = await admin_client.get("/officers/current")
    assert response.status_code == 200
    curr_officers = response.json()
    assert len(curr_officers) == 6
    officer = next(o for o in curr_officers if o["position"] == OfficerPositionEnum.EXECUTIVE_AT_LARGE)
    assert "computing_id" in officer
    assert "discord_id" in officer
    assert "discord_name" in officer
    assert "discord_nickname" in officer
    assert "phone_number" in officer
    assert "github_username" in officer
    assert "google_drive_email" in officer
    assert "photo_url" in officer


async def test__get_all_officers_admin(admin_client: AsyncClient):
    response = await admin_client.get("/officers/all?include_future_terms=true")
    assert response.status_code == 200
    assert len(response.json()) == 9
    assert response.json()[1]["phone_number"] == "1234567890"


async def test__admin_get_officer_term(admin_client: AsyncClient):
    response = await admin_client.get(
        f"/officers/terms/{load_test_db.SYSADMIN_COMPUTING_ID}?include_future_terms=false"
    )
    assert response.status_code == 200
    assert response.json() != []
    assert len(response.json()) == 2


async def test__admin_get_officer_term_with_future(admin_client: AsyncClient):
    response = await admin_client.get(f"/officers/terms/{load_test_db.SYSADMIN_COMPUTING_ID}?include_future_terms=true")
    assert response.status_code == 200
    assert response.json() != []
    assert len(response.json()) == 3


async def test__admin_get_other_officer_term_with_future(admin_client: AsyncClient):
    response = await admin_client.get("/officers/terms/ehbc12?include_future_terms=true")
    assert response.status_code == 200
    assert response.json() == []


async def test__get_single_valid_officer_info(admin_client: AsyncClient):
    response = await admin_client.get("/officers/info/abc11")
    assert response.status_code == 200
    assert response.json() != {}
    assert response.json()["legal_name"] == "Person A"
    response = await admin_client.get(f"/officers/info/{load_test_db.SYSADMIN_COMPUTING_ID}")
    assert response.status_code == 200
    assert response.json() != {}
    response = await admin_client.get("/officers/info/balargho")
    assert response.status_code == 404


async def test__admin_create_officer_term(admin_client: AsyncClient):
    response = await admin_client.post(
        "officers/term",
        json=[
            {
                "computing_id": "ehbc12",
                "position": OfficerPositionEnum.DIRECTOR_OF_MULTIMEDIA,
                "start_date": "2026-12-29",
                "legal_name": "Eh Bc",
            }
        ],
    )
    assert response.status_code == 200

    response = await admin_client.get("/officers/terms/ehbc12?include_future_terms=true")
    assert response.status_code == 200
    assert response.json() != []
    assert len(response.json()) == 1


async def test__admin_patch_officer_info(admin_client: AsyncClient):
    response = await admin_client.patch(
        "officers/info/abc11",
        content=json.dumps(
            {
                "legal_name": "Person A2",
                "phone_number": "12345asdab67890",
                "discord_name": "person_a_yeah",
                "github_username": "person_a",
                "google_drive_email": "person_a@gmail.com",
            }
        ),
    )
    assert response.status_code == 200
    resJson = response.json()
    assert resJson["legal_name"] == "Person A2"
    assert resJson["phone_number"] == "12345asdab67890"
    assert resJson["discord_name"] == "person_a_yeah"
    assert resJson["github_username"] == "person_a"
    assert resJson["google_drive_email"] == "person_a@gmail.com"

    response = await admin_client.patch(
        "officers/info/aaabbbc",
        content=json.dumps(
            {
                "legal_name": "Person AABBCC",
                "phone_number": "1234567890",
                "discord_name": None,
                "github_username": None,
                "google_drive_email": "person_aaa_bbb_ccc+spam@gmail.com",
            }
        ),
    )
    assert response.status_code == 404


async def test__admin_patch_officer_term(admin_client: AsyncClient):
    target_id = 1
    response = await admin_client.patch(
        f"officers/term/{target_id}",
        json={
            "position": OfficerPositionEnum.TREASURER,
            "start_date": (date.today() - timedelta(days=365)).isoformat(),
            "end_date": (date.today() - timedelta(days=1)).isoformat(),
            "nickname": "1",
            "favourite_course_0": "2",
            "favourite_course_1": "3",
            "favourite_pl_0": "4",
            "favourite_pl_1": "5",
            "biography": "hello o77",
        },
    )
    assert response.status_code == 200

    response = await admin_client.get("/officers/terms/abc11?include_future_terms=true")
    assert response.status_code == 200
    modifiedTerm = next((item for item in response.json() if item["id"] == target_id), None)
    assert modifiedTerm is not None
    assert modifiedTerm["position"] == OfficerPositionEnum.TREASURER
    assert modifiedTerm["start_date"] == (date.today() - timedelta(days=365)).isoformat()
    assert modifiedTerm["end_date"] == (date.today() - timedelta(days=1)).isoformat()
    assert modifiedTerm["nickname"] == "1"
    assert modifiedTerm["favourite_course_0"] == "2"
    assert modifiedTerm["favourite_course_1"] == "3"
    assert modifiedTerm["favourite_pl_0"] == "4"
    assert modifiedTerm["favourite_pl_1"] == "5"
    assert modifiedTerm["biography"] == "hello o77"

    # other one shouldn't be modified
    assert response.status_code == 200
    modifiedTerm = next((item for item in response.json() if item["id"] == target_id + 1), None)
    assert modifiedTerm is not None
    assert modifiedTerm["position"] == OfficerPositionEnum.EXECUTIVE_AT_LARGE
    assert modifiedTerm["start_date"] != (date.today() - timedelta(days=365)).isoformat()
    assert modifiedTerm["end_date"] != (date.today() - timedelta(days=1)).isoformat()
    assert modifiedTerm["nickname"] != "1"
    assert modifiedTerm["favourite_course_0"] != "2"
    assert modifiedTerm["favourite_course_1"] != "3"
    assert modifiedTerm["favourite_pl_0"] != "4"
    assert modifiedTerm["favourite_pl_1"] != "5"
    assert modifiedTerm["biography"] != "hello o77"

    response = await admin_client.get("officers/all?include_future_terms=True")
    assert len(response.json()) == 10

    response = await admin_client.delete("officers/term/1")
    assert response.status_code == 200
    response = await admin_client.delete("officers/term/2")
    assert response.status_code == 200
    response = await admin_client.delete("officers/term/3")
    assert response.status_code == 200
    response = await admin_client.delete("officers/term/4")
    assert response.status_code == 200

    response = await admin_client.get("officers/all?include_future_terms=True")
    assert len(response.json()) == 6
