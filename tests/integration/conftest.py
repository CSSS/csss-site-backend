# Configuration of Pytest
from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from auth.crud import create_user_session, remove_user_session
from database import SQLALCHEMY_TEST_DATABASE_URL, DatabaseSessionManager, get_db_session
from load_test_db import SYSADMIN_COMPUTING_ID, async_main
from main import app


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def test_database():
    # reset the database again, just in case
    print("Resetting DB...")
    sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": False}, check_db=False)
    # this resets the contents of the database to be whatever is from `load_test_db.py`
    await async_main(sessionmanager)
    print("Done setting up!")
    yield sessionmanager
    await sessionmanager.close()


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def db_session(test_database: DatabaseSessionManager):
    async with test_database.session() as session:
        yield session


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def client(test_database: DatabaseSessionManager) -> AsyncGenerator[Any]:
    async def override_get_db_session():
        async with test_database.session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    # base_url is just a random placeholder url
    # ASGITransport is just telling the async client to pass all requests to app
    # `async with` syntax used so that the connecton will automatically be closed once done
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def admin_client(test_database: DatabaseSessionManager, client: AsyncClient):
    session_id = "temp_id_" + SYSADMIN_COMPUTING_ID
    client.cookies = {"session_id": session_id}
    async with test_database.session() as session:
        await create_user_session(session, session_id, SYSADMIN_COMPUTING_ID)
        yield client
        await remove_user_session(session, session_id)
