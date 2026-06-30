from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from database import get_db_session
from translink.urls import router as translink_router


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def client() -> AsyncGenerator[Any]:
    app = FastAPI()
    app.include_router(translink_router)
    app.state.http_client = AsyncMock(spec=AsyncClient)

    async def override_get_db_session():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client
