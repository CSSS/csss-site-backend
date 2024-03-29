import os
import contextlib
from typing import Any, Annotated, AsyncIterator

from fastapi import FastAPI, Depends

import sqlalchemy
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
)

#Base = sqlalchemy.ext.declarative.declarative_base()
Base = sqlalchemy.orm.declarative_base()

# from: https://medium.com/@tclaitken/setting-up-a-fastapi-app-with-async-sqlalchemy-2-0-pydantic-v2-e6c540be4308
class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any] = {}):
        #engine = sqlalchemy.create_engine(SQLALCHEMY_DATABASE_URL)
        self._engine = sqlalchemy.ext.asyncio.create_async_engine(host, **engine_kwargs)
        #SessionLocal = sqlalchemy.orm.sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self._sessionmaker = sqlalchemy.ext.asyncio.async_sessionmaker(autocommit=False, bind=self._engine)

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

SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg:///main"

# TODO: where is sys.stdout piped to? I want all these to go to a specific logs folder
sessionmanager = DatabaseSessionManager(SQLALCHEMY_DATABASE_URL, { "echo": True })

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

DBSession = Annotated[AsyncSession, Depends(_db_session)]
