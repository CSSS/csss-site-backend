from unittest.mock import AsyncMock

import pytest
from fastapi.responses import JSONResponse

import elections.crud
from elections.urls import list_elections

pytestmark = pytest.mark.unit


async def test__list_elections_returns_empty_list_when_none_exist(monkeypatch: pytest.MonkeyPatch):
    db_session = AsyncMock()
    monkeypatch.setattr(elections.crud, "get_all_elections", AsyncMock(return_value=[]))

    response = await list_elections(computing_id=None, db_session=db_session, with_nominees=False)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert response.body == b"[]"


async def test__list_elections_with_nominees_returns_empty_list_when_none_exist(monkeypatch: pytest.MonkeyPatch):
    db_session = AsyncMock()
    monkeypatch.setattr(elections.crud, "get_all_elections_with_nominees", AsyncMock(return_value=[]))

    response = await list_elections(computing_id=None, db_session=db_session, with_nominees=True)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    assert response.body == b"[]"
