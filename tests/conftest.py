# Configuration of Pytest
import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src import load_test_db
from src.auth.crud import create_user_session
from src.database import SQLALCHEMY_TEST_DATABASE_URL, DatabaseSessionManager
from src.main import app


# This might be able to be moved to `package` scope as long as I inject it to every test function
@pytest.fixture(scope="session")
def suppress_sqlalchemy_logs():
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    yield
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[Any, None]:
    # base_url is just a random placeholder url
    # ASGITransport is just telling the async client to pass all requests to app
    # `async with` syntax used so that the connecton will automatically be closed once done
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client

@pytest_asyncio.fixture(scope="module")
async def database_setup():
    # reset the database again, just in case
    print("Resetting DB...")
    sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": False}, check_db=False)
    # this resets the contents of the database to be whatever is from `load_test_db.py`
    await load_test_db.async_main(sessionmanager)
    print("Done setting up!")
    yield sessionmanager
    await sessionmanager.close()

@pytest_asyncio.fixture(scope="function")
async def db_transaction(database_setup):
    async with database_setup.session() as session:
        try:
            await session.begin()
            yield session
        finally:
            await session.rollback()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_transaction):
    yield db_transaction

@pytest_asyncio.fixture(scope="function")
async def admin_session(database_setup):
    session_id = "temp_id_" + load_test_db.SYSADMIN_COMPUTING_ID
    async with database_setup.session() as db_session:
        await create_user_session(db_session, session_id, load_test_db.SYSADMIN_COMPUTING_ID)
    yield


