from uuid import uuid4

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from auth.constants import COOKIE_SESSION_KEY, UserRole
from auth.crud import create_user_session, get_site_user_by_computing_id
from auth.tables import AuthRedirectDB, SiteUserDB, SiteUserRoleDB, UserSessionDB
from config import settings
from database import SQLALCHEMY_TEST_DATABASE_URL, Base, get_db_session
from main import app
from officers.tables import OfficerInfoDB, OfficerPositionDB, OfficerPositionVersionDB, OfficerTermDB


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def db_connection():
    """Avoid the shared legacy seed and roll back the schema and extension after each test."""
    schema = f"uid_identity_{uuid4().hex}"
    engine = create_async_engine(SQLALCHEMY_TEST_DATABASE_URL)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.execute(text(f"CREATE SCHEMA {schema}"))
        await connection.execute(text(f"SET LOCAL search_path TO {schema}, public"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))

        def create_tables(conn: Connection):
            models = (
                SiteUserDB,
                SiteUserRoleDB,
                UserSessionDB,
                AuthRedirectDB,
                OfficerInfoDB,
                OfficerPositionDB,
                OfficerPositionVersionDB,
                OfficerTermDB,
            )
            Base.metadata.create_all(conn, tables=[Base.metadata.tables[model.__tablename__] for model in models])

        await connection.run_sync(create_tables)
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def db_session(db_connection):
    async with AsyncSession(bind=db_connection, join_transaction_mode="create_savepoint") as session:
        yield session


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def client(db_connection, monkeypatch):
    monkeypatch.setattr(settings, "allowed_origins", ["http://frontend.test"])

    async def get_session():
        async with AsyncSession(bind=db_connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_db_session] = get_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app), base_url="http://test", headers={"Origin": "http://frontend.test"}
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function", loop_scope="session")
async def admin_client(client, db_session):
    await create_user_session(db_session, "uid-admin-session", "uidadmin")
    admin = await get_site_user_by_computing_id(db_session, "uidadmin")
    assert admin is not None
    db_session.add(SiteUserRoleDB(uid=admin.uid, role=UserRole.ACCESS))
    await db_session.commit()
    client.cookies.set(COOKIE_SESSION_KEY, "uid-admin-session", domain="test.local", path="/")
    yield client
