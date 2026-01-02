import json
from datetime import date, timedelta
from http import HTTPStatus

import pytest
from fastapi import status
from httpx import AsyncClient

import load_test_db
from officers.constants import OfficerPositionEnum
from officers.crud import current_officers, get_active_officer_terms, get_all_officers

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEST_NOMINEE = {
    "computing_id": "test",
    "full_name": "Test Nominee",
    "linked_in": "tested_in",
    "instagram": "testagram",
    "email": "test@test.com",
    "discord_username": "testcord#1234",
}

PATCH_NOMINEE = {
    "full_name": "New Name",
    "linked_in": "new_linked_in",
    "instagram": "new_instagram",
    "email": "new@email.com",
    "discord_username": "new_discord#5678",
}

# TODO: Modify the test database to be empty


# Unauthenticated requests
async def test__create_nominees(client: AsyncClient):
    response = await client.post("/nominee", json=TEST_NOMINEE)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test__get_nominees(client: AsyncClient):
    response = await client.get("/nominee")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test__get_one_nominee(client: AsyncClient):
    response = await client.get(f"/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test__update_nominee(client: AsyncClient):
    response = await client.patch(f"/nominee/{TEST_NOMINEE['computing_id']}", json=PATCH_NOMINEE)
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test__delete_nominee(client: AsyncClient):
    response = await client.delete(f"/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


# TODO: Test an election officer trying to change other election information
# TODO: Write the election officer tests
# Election Officer requests
# async def test__admin_create_nominees(admin_client: AsyncClient):
#     response = await admin_client.post("/nominee", json=TEST_NOMINEE)
#     assert response.status_code == HTTPStatus.OK
#     assert TEST_NOMINEE == response.json()
#
#
# async def test__admin_get_nominees(admin_client: AsyncClient):
#     response = await admin_client.get("/nominee")
#     assert response.status_code == HTTPStatus.OK
#     # FIXME: This should be 2 if the test database is empty
#     assert len(response.json()) == 3
#
#
# async def test__admin_get_one_nominee(admin_client: AsyncClient):
#     response = await admin_client.get(f"/nominee/{TEST_NOMINEE['computing_id']}")
#     assert response.status_code == HTTPStatus.OK
#
#
# async def test__admin_update_nominee(admin_client: AsyncClient):
#     response = await admin_client.patch(f"/nominee/{TEST_NOMINEE['computing_id']}", json={"full_name": "Should Fail"})
#     assert response.status_code == HTTPStatus.OK
#
#
# async def test__admin_delete_nominee(admin_client: AsyncClient):
#     response = await admin_client.delete(f"/nominee/{TEST_NOMINEE['computing_id']}")
#     assert response.status_code == HTTPStatus.OK


# Admin requests
async def test__admin_create_nominees(admin_client: AsyncClient):
    response = await admin_client.post("/nominee", json=TEST_NOMINEE)
    assert response.status_code == HTTPStatus.OK
    assert TEST_NOMINEE == response.json()


async def test__admin_get_nominees(admin_client: AsyncClient):
    response = await admin_client.get("/nominee")
    assert response.status_code == HTTPStatus.OK
    # FIXME: This should be 1 if the test database is empty
    assert len(response.json()) == 3
    test_nominee = next(n for n in response.json() if n["computing_id"] == TEST_NOMINEE["computing_id"])
    assert test_nominee == TEST_NOMINEE


async def test__admin_get_one_nominee(admin_client: AsyncClient):
    response = await admin_client.get(f"/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == TEST_NOMINEE


async def test__admin_update_nominee(admin_client: AsyncClient):
    response = await admin_client.patch(
        f"/nominee/{TEST_NOMINEE['computing_id']}",
        json={
            "computing_id": "should_not_change",
        },
    )
    assert response.status_code == 200
    assert response.json() == TEST_NOMINEE

    response = await admin_client.patch(
        f"/nominee/{TEST_NOMINEE['computing_id']}",
        json=PATCH_NOMINEE,
    )
    assert response.status_code == HTTPStatus.OK
    expected_response = dict(PATCH_NOMINEE)
    expected_response["computing_id"] = TEST_NOMINEE["computing_id"]
    assert response.json() == expected_response


async def test__admin_delete_nominee(admin_client: AsyncClient):
    response = await admin_client.delete(f"/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == HTTPStatus.OK
    assert response.json()["success"]
