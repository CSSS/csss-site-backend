from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app


@pytest_asyncio.fixture(scope="module", loop_scope="session")
async def client() -> AsyncGenerator[Any]:
    app.state.http_client = AsyncMock(spec=AsyncClient)
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client
