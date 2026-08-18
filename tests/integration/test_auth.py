from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest
import sqlalchemy
from httpx import AsyncClient, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import CAS_VALIDATE_URL, COOKIE_MAX_AGE, COOKIE_SESSION_KEY, SESSION_MAX_AGE
from auth.crud import create_user_session
from auth.tables import UserSessionDB
from config import settings
from main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEST_SERVICE = "http://localhost:8080"
TEST_TICKET = "ST-test-ticket"
TEST_COMPUTING_ID = "auth123"


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "cookie_domain", None)


def _cas_response(content: str, status_code: int = HTTPStatus.OK) -> Response:
    return Response(
        status_code=status_code,
        text=content,
        request=Request("GET", CAS_VALIDATE_URL),
    )


def _mock_cas_response(monkeypatch: pytest.MonkeyPatch, content: str, status_code: int = HTTPStatus.OK) -> AsyncMock:
    client = AsyncMock(spec=AsyncClient)
    client.get = AsyncMock(return_value=_cas_response(content, status_code))
    monkeypatch.setattr(app.state, "http_client", client, raising=False)
    return client


def _successful_cas_xml(computing_id: str = TEST_COMPUTING_ID) -> str:
    return f"""
    <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
        <cas:authenticationSuccess>
            <cas:user>{computing_id}</cas:user>
        </cas:authenticationSuccess>
    </cas:serviceResponse>
    """


def _failed_cas_xml() -> str:
    return """
    <cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas">
        <cas:authenticationFailure code="INVALID_TICKET">
            Ticket validation failed
        </cas:authenticationFailure>
    </cas:serviceResponse>
    """
