from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

import elections.crud
from database import get_db_session
from elections.urls import router

pytestmark = pytest.mark.unit


@pytest_asyncio.fixture
async def election_client():
    app = FastAPI()
    app.include_router(router)

    async def override_get_db_session():
        yield AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as client:
        yield client


@pytest.mark.parametrize(
    ("query", "with_nominees"),
    [("", False), ("?with_nominees=false", False), ("?with_nominees=true", True)],
)
async def test__empty_election_list_returns_ok(
    election_client: AsyncClient, monkeypatch: pytest.MonkeyPatch, query, with_nominees
):
    get_all = AsyncMock(return_value=[])
    get_with_nominees = AsyncMock(return_value=[])
    monkeypatch.setattr(elections.crud, "get_all_elections", get_all)
    monkeypatch.setattr(elections.crud, "get_all_elections_with_nominees", get_with_nominees)

    response = await election_client.get(f"/election{query}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []
    if with_nominees:
        get_with_nominees.assert_awaited_once()
        get_all.assert_not_awaited()
    else:
        get_all.assert_awaited_once()
        get_with_nominees.assert_not_awaited()


async def test__missing_election_still_returns_not_found(election_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    get_election = AsyncMock(return_value=None)
    monkeypatch.setattr(elections.crud, "get_election", get_election)

    response = await election_client.get("/election/missing")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "election with slug missing does not exist"}
    get_election.assert_awaited_once()


async def test__election_list_schema_does_not_advertise_not_found(election_client: AsyncClient):
    response = await election_client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
    paths = response.json()["paths"]

    assert "200" in paths["/election"]["get"]["responses"]
    assert "404" not in paths["/election"]["get"]["responses"]
    assert "404" in paths["/election/{election_name}"]["get"]["responses"]
