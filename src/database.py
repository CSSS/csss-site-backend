import asyncio
import contextlib
import os
from collections.abc import AsyncIterator
from typing import Annotated, Any

import asyncpg
import sqlalchemy
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
)

# Base = sqlalchemy.ext.declarative.declarative_base()
Base = sqlalchemy.orm.declarative_base()

# from: https://medium.com/@tclaitken/setting-up-a-fastapi-app-with-async-sqlalchemy-2-0-pydantic-v2-e6c540be4308
class DatabaseSessionManager:
    def __init__(self, db_url: str, engine_kwargs: dict[str, Any], check_db=True):
        # engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URL)
        self._engine = sqlalchemy.ext.asyncio.create_async_engine(db_url, **engine_kwargs)
        # SessionLocal = sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self._sessionmaker = sqlalchemy.ext.asyncio.async_sessionmaker(autocommit=False, bind=self._engine)

        if check_db:
            # check if the database exists by making a test connection
            # NOTE: don't do this in an async function
            asyncio.run(DatabaseSessionManager.test_connection(db_url))

    # test if the database is working & raise an exception if not
    @staticmethod
    async def test_connection(sqlalchemy_db_url: str):
        try:
            asyncpg_db_url = sqlalchemy_db_url.replace("+asyncpg", "")
            conn = await asyncpg.connect(asyncpg_db_url)
            await conn.close()
        except Exception as e:
            raise Exception(f"Could not connect to {sqlalchemy_db_url}. Postgres database might not exist. Got: {e}") from e

        # TODO: setup logging
        print(f"successful connection test to {sqlalchemy_db_url}")

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


if os.environ.get("DB_PORT") is not None:
    db_port = os.environ.get("DB_PORT")
    SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://localhost:{db_port}/main"
    SQLALCHEMY_TEST_DATABASE_URL = f"postgresql+asyncpg://localhost:{db_port}/test"
else:
    SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg:///main"
    SQLALCHEMY_TEST_DATABASE_URL = "postgresql+asyncpg:///test"

# also TODO: make this nicer, using a class to hold state...
# and use this in load_test_db for the test db as well?
def setup_database():
    global sessionmanager

    # TODO: where is sys.stdout piped to? I want all these to go to a specific logs folder
    if os.environ.get("LOCAL"):
        sessionmanager = DatabaseSessionManager(SQLALCHEMY_TEST_DATABASE_URL, {"echo": True})
    else:
        sessionmanager = DatabaseSessionManager(SQLALCHEMY_DATABASE_URL, {"echo": True})

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events, see https://fastapi.tiangolo.com/advanced/events/
    """
    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()


async def _db_session():
    async with sessionmanager.session() as session:
        yield session


# TODO: what does this do again?
DBSession = Annotated[AsyncSession, Depends(_db_session)]
