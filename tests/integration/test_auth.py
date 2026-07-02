from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest
import sqlalchemy
from httpx import AsyncClient, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import COOKIE_MAX_AGE, COOKIE_SESSION_KEY, SESSION_MAX_AGE
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
    monkeypatch.setattr(settings, "auth_url", "https://cas.sfu.ca/cas/serviceValidate")
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "cookie_domain", None)


def _cas_response(content: str, status_code: int = HTTPStatus.OK) -> Response:
    return Response(
        status_code=status_code,
        text=content,
        request=Request("GET", settings.auth_url or "https://cas.example.test/serviceValidate"),
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


async def test__login_creates_session_cookie_and_get_user(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    client.cookies.clear()
    cas_client = _mock_cas_response(monkeypatch, _successful_cas_xml())

    response = await client.post("/auth/login", json={"service": TEST_SERVICE, "ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert COOKIE_SESSION_KEY in client.cookies

    set_cookie = response.headers["set-cookie"]
    assert f"{COOKIE_SESSION_KEY}=" in set_cookie
    assert f"Max-Age={COOKIE_MAX_AGE}" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie

    cas_client.get.assert_awaited_once()

    response = await client.get("/auth/user")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["computing_id"] == TEST_COMPUTING_ID
    assert response.json()["first_logged_in"] is not None
    assert response.json()["last_logged_in"] is not None


async def test__login_returns_unauthorized_for_failed_cas_ticket(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    client.cookies.clear()
    _mock_cas_response(monkeypatch, _failed_cas_xml())

    response = await client.post("/auth/login", json={"service": TEST_SERVICE, "ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert COOKIE_SESSION_KEY not in client.cookies


async def test__login_returns_bad_gateway_for_cas_connection_failure(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    client.cookies.clear()
    _mock_cas_response(monkeypatch, "CAS unavailable", HTTPStatus.SERVICE_UNAVAILABLE)

    response = await client.post("/auth/login", json={"service": TEST_SERVICE, "ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert COOKIE_SESSION_KEY not in client.cookies


async def test__login_returns_service_unavailable_when_auth_is_not_configured(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    client.cookies.clear()
    cas_client = _mock_cas_response(monkeypatch, _successful_cas_xml())
    monkeypatch.setattr(settings, "auth_url", None)

    response = await client.post("/auth/login", json={"service": TEST_SERVICE, "ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    cas_client.get.assert_not_awaited()
    assert COOKIE_SESSION_KEY not in client.cookies


async def test__logout_is_idempotent_and_deletes_session_cookie(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    client.cookies.clear()

    response = await client.get("/auth/logout")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "logout successful"}

    _mock_cas_response(monkeypatch, _successful_cas_xml())
    response = await client.post("/auth/login", json={"service": TEST_SERVICE, "ticket": TEST_TICKET})
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert COOKIE_SESSION_KEY in client.cookies

    response = await client.get("/auth/logout")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"message": "logout successful"}
    assert COOKIE_SESSION_KEY not in client.cookies
    assert f"{COOKIE_SESSION_KEY}=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]

    response = await client.get("/auth/user")
    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test__expired_session_cannot_get_user(client: AsyncClient, db_session: AsyncSession):
    client.cookies.clear()
    session_id = "expired-session-id"
    computing_id = "expired"
    await create_user_session(db_session, session_id, computing_id)
    await db_session.execute(
        sqlalchemy.update(UserSessionDB)
        .where(UserSessionDB.session_id == session_id)
        .values(issue_time=datetime.now(UTC) - (2 * SESSION_MAX_AGE))
    )
    await db_session.commit()
    client.cookies.set(COOKIE_SESSION_KEY, session_id)

    response = await client.get("/auth/user")

    assert response.status_code == HTTPStatus.UNAUTHORIZED
