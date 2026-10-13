import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import create_user_session, get_site_user_by_computing_id
from auth.tables import SiteUserRoleDB
from database import DBSession
from nominees.crud import create_nominee_info, get_nominee_info
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


@pytest_asyncio.fixture(loop_scope="session")
async def admin_client(client: AsyncClient, db_session: DBSession):
    session_id = "nominee-admin-session"
    await create_user_session(db_session, session_id, "nomadmin")
    user = await get_site_user_by_computing_id(db_session, "nomadmin")
    assert user is not None
    db_session.add(SiteUserRoleDB(uid=user.uid, role=UserRole.ADMIN))
    await db_session.commit()
    client.cookies.set(COOKIE_SESSION_KEY, session_id, domain="test.local", path="/")
    yield client


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


# Admin requests
async def test__admin_create_nominees(admin_client: AsyncClient):
    response = await admin_client.post("/api/nominee", json=TEST_NOMINEE)
    assert response.status_code == status.HTTP_200_OK
    assert TEST_NOMINEE == response.json()


async def test__admin_get_nominees(db_session: DBSession, admin_client: AsyncClient):
    await insert_test_nominee(db_session)
    second = {**TEST_NOMINEE, "computing_id": "testsecond", "full_name": "Second Nominee"}
    await create_nominee_info(db_session, NomineeInfoDB(**second))
    await db_session.commit()
    response = await admin_client.get("/api/nominee")
    assert response.status_code == status.HTTP_200_OK
    nominees = {nominee["computing_id"]: nominee for nominee in response.json()}
    assert nominees[TEST_NOMINEE["computing_id"]] == TEST_NOMINEE
    assert nominees[second["computing_id"]] == second


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


async def test__admin_delete_nominee(db_session: DBSession, admin_client: AsyncClient):
    await insert_test_nominee(db_session)
    response = await admin_client.delete(f"/api/nominee/{TEST_NOMINEE['computing_id']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert await get_nominee_info(db_session, TEST_NOMINEE["computing_id"]) is None
