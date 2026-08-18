# Configuration of Pytest
from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from auth.constants import COOKIE_SESSION_KEY
from auth.crud import create_user_session, remove_user_session_by_id
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
async def db_connection(test_database: DatabaseSessionManager):
    async with test_database.engine.connect() as connection:
        transaction = await connection.begin()

        try:
            yield connection
        finally:
            await transaction.rollback()


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def db_session(db_connection: AsyncConnection):
    async with AsyncSession(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
    ) as session:
        yield session


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def client(db_connection: AsyncConnection) -> AsyncGenerator[AsyncClient]:
    async def override_get_db_session():
        async with AsyncSession(
            bind=db_connection,
            join_transaction_mode="create_savepoint",
        ) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    # base_url is just a random placeholder url
    # ASGITransport is just telling the async client to pass all requests to app
    # `async with` syntax used so that the connecton will automatically be closed once done
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def admin_client(db_connection: AsyncConnection, client: AsyncClient):
    session_id = "temp_id_" + SYSADMIN_COMPUTING_ID
    client.cookies = {COOKIE_SESSION_KEY: session_id}
    async with AsyncSession(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
    ) as session:
        await create_user_session(session, session_id, SYSADMIN_COMPUTING_ID)
        await session.commit()

    yield client
