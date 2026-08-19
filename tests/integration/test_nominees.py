import pytest
from fastapi import status
from httpx import AsyncClient

from database import DBSession
from nominees.crud import create_nominee_info
from nominees.tables import NomineeInfoDB

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


async def insert_test_nominee(db_session: DBSession):
    await create_nominee_info(db_session, NomineeInfoDB(**TEST_NOMINEE))
    await db_session.commit()


# TODO: Modify the test database to be empty


# Unauthenticated requests
async def test__create_nominees(client: AsyncClient):
    response = await client.post("/api/nominee", json=TEST_NOMINEE)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__get_nominees(client: AsyncClient):
    response = await client.get("/api/nominee")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__get_one_nominee(client: AsyncClient):
    response = await client.get(f"/api/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__update_nominee(client: AsyncClient):
    response = await client.patch(f"/api/nominee/{TEST_NOMINEE['computing_id']}", json=PATCH_NOMINEE)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__delete_nominee(client: AsyncClient):
    response = await client.delete(f"/api/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# TODO: Test an election officer trying to change other election information
# TODO: Write the election officer tests
# Election Officer requests
# async def test__admin_create_nominees(admin_client: AsyncClient):
#     response = await admin_client.post("/api/nominee", json=TEST_NOMINEE)
#     assert response.status_code == status.HTTP_200_OK
#     assert TEST_NOMINEE == response.json()
#
#
# async def test__admin_get_nominees(admin_client: AsyncClient):
#     response = await admin_client.get("/api/nominee")
#     assert response.status_code == status.HTTP_200_OK
#     # FIXME: This should be 2 if the test database is empty
#     assert len(response.json()) == 3
#
#
# async def test__admin_get_one_nominee(admin_client: AsyncClient):
#     response = await admin_client.get(f"/api/nominee/{TEST_NOMINEE['computing_id']}")
#     assert response.status_code == status.HTTP_200_OK
#
#
# async def test__admin_update_nominee(admin_client: AsyncClient):
#     response = await admin_client.patch(f"/api/nominee/{TEST_NOMINEE['computing_id']}", json={"full_name": "Should Fail"})
#     assert response.status_code == status.HTTP_200_OK
#
#
# async def test__admin_delete_nominee(admin_client: AsyncClient):
#     response = await admin_client.delete(f"/api/nominee/{TEST_NOMINEE['computing_id']}")
#     assert response.status_code == status.HTTP_200_OK


# Admin requests
async def test__admin_create_nominees(admin_client: AsyncClient):
    response = await admin_client.post("/api/nominee", json=TEST_NOMINEE)
    assert response.status_code == status.HTTP_200_OK
    assert TEST_NOMINEE == response.json()


async def test__admin_get_nominees(admin_client: AsyncClient):
    # TODO: Add inserts
    response = await admin_client.get("/api/nominee")
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


async def test__admin_get_one_nominee(db_session: DBSession, admin_client: AsyncClient):
    await insert_test_nominee(db_session)
    response = await admin_client.get(f"/api/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == TEST_NOMINEE


async def test__admin_update_nominee(db_session: DBSession, admin_client: AsyncClient):
    await insert_test_nominee(db_session)
    response = await admin_client.patch(
        f"/api/nominee/{TEST_NOMINEE['computing_id']}",
        json={
            "computing_id": "should_not_change",
        },
    )
    assert response.status_code == 200
    assert response.json() == TEST_NOMINEE

    response = await admin_client.patch(
        f"/api/nominee/{TEST_NOMINEE['computing_id']}",
        json=PATCH_NOMINEE,
    )
    assert response.status_code == status.HTTP_200_OK
    expected_response = dict(PATCH_NOMINEE)
    expected_response["computing_id"] = TEST_NOMINEE["computing_id"]
    assert response.json() == expected_response


async def test__admin_delete_nominee(admin_client: AsyncClient):
    response = await admin_client.delete(f"/api/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]
