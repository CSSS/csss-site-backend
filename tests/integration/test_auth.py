import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from http import HTTPStatus
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import sqlalchemy
from httpx import AsyncClient, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from auth.constants import (
    CAS_LOGIN_URL,
    CAS_VALIDATE_URL,
    COOKIE_AUTH_REDIRECT_KEY,
    COOKIE_MAX_AGE,
    COOKIE_SAMESITE,
    COOKIE_SESSION_KEY,
    REDIRECT_TTL,
    UserRole,
)
from auth.crud import create_user_session
from auth.tables import AuthRedirectDB, SiteUserRoleDB, UserSessionDB
from config import settings
from main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEST_APP_URL = "http://api.test"
TEST_RETURN_ORIGIN = "http://frontend.test"
TEST_RETURN_TO = f"{TEST_RETURN_ORIGIN}/login-complete?source=cas"
TEST_TICKET = "ST-test-ticket"
TEST_COMPUTING_ID = "auth123"


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "environment", "test")
    monkeypatch.setattr(settings, "app_url", TEST_APP_URL)
    monkeypatch.setattr(settings, "allowed_return_origins", [TEST_RETURN_ORIGIN])
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "cookie_domain", None)


def _cas_response(content: str, status_code: int = HTTPStatus.OK) -> Response:
    return Response(
        status_code=status_code,
        text=content,
        request=Request("GET", CAS_VALIDATE_URL),
    )


def _mock_cas_response(monkeypatch: pytest.MonkeyPatch, content: str, status_code: int = HTTPStatus.OK) -> AsyncMock:
    cas_client = AsyncMock(spec=AsyncClient)
    cas_client.get = AsyncMock(return_value=_cas_response(content, status_code))
    monkeypatch.setattr(app.state, "http_client", cas_client, raising=False)
    return cas_client


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


def _session_hash(session_id: str) -> bytes:
    return sha256(session_id.encode("utf-8")).digest()


async def _start_login(client: AsyncClient, return_to: str = TEST_RETURN_TO) -> tuple[Response, str]:
    response = await client.get("/auth/login", params={"return_to": return_to})
    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT

    token = client.cookies.get(COOKIE_AUTH_REDIRECT_KEY)
    assert token is not None
    return response, token


async def _create_logged_in_client(
    db_session: AsyncSession,
    client: AsyncClient,
    session_id: str,
    computing_id: str,
    role: UserRole | None = None,
) -> bytes:
    session_hash = await create_user_session(db_session, session_id, computing_id)
    if role is not None:
        db_session.add(SiteUserRoleDB(computing_id=computing_id, role=role, added_by=None))
    await db_session.commit()
    client.cookies.set(COOKIE_SESSION_KEY, session_id, domain="test.local", path="/")
    return session_hash


async def test__login_creates_cas_redirect_and_stores_return_url(client: AsyncClient, db_session: AsyncSession):
    client.cookies.clear()

    response, token = await _start_login(client)

    location = urlsplit(response.headers["location"])
    cas_login_url = urlsplit(CAS_LOGIN_URL)
    assert (location.scheme, location.netloc, location.path) == (
        cas_login_url.scheme,
        cas_login_url.netloc,
        cas_login_url.path,
    )
    assert parse_qs(location.query) == {"service": [f"{TEST_APP_URL}/auth/validate"]}

    set_cookie = response.headers["set-cookie"]
    assert f"{COOKIE_AUTH_REDIRECT_KEY}={token}" in set_cookie
    assert f"Max-Age={REDIRECT_TTL}" in set_cookie
    assert "HttpOnly" in set_cookie
    assert f"SameSite={COOKIE_SAMESITE}" in set_cookie

    auth_redirect = await db_session.get(AuthRedirectDB, token)
    assert auth_redirect is not None
    assert auth_redirect.return_to == TEST_RETURN_TO
    assert auth_redirect.expires_at > datetime.now(UTC)


async def test__login_uses_original_url_header_when_return_to_is_omitted(
    client: AsyncClient,
    db_session: AsyncSession,
):
    client.cookies.clear()

    response = await client.get(
        "/auth/login",
        headers={"X-Original-URL": TEST_RETURN_TO},
    )

    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    token = client.cookies.get(COOKIE_AUTH_REDIRECT_KEY)
    assert token is not None
    auth_redirect = await db_session.get(AuthRedirectDB, token)
    assert auth_redirect is not None
    assert auth_redirect.return_to == TEST_RETURN_TO


async def test__login_rejects_missing_return_url(client: AsyncClient):
    client.cookies.clear()

    response = await client.get("/auth/login")

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {"detail": "Missing return URL"}
    assert COOKIE_AUTH_REDIRECT_KEY not in client.cookies


async def test__login_validates_original_url_header(client: AsyncClient):
    client.cookies.clear()

    response = await client.get(
        "/auth/login",
        headers={"X-Original-URL": "http://untrusted.test/path"},
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert COOKIE_AUTH_REDIRECT_KEY not in client.cookies


async def test__login_prefers_return_to_over_original_url_header(
    client: AsyncClient,
    db_session: AsyncSession,
):
    client.cookies.clear()

    response = await client.get(
        "/auth/login",
        params={"return_to": TEST_RETURN_TO},
        headers={"X-Original-URL": "http://untrusted.test/path"},
    )

    assert response.status_code == HTTPStatus.TEMPORARY_REDIRECT
    token = client.cookies.get(COOKIE_AUTH_REDIRECT_KEY)
    assert token is not None
    auth_redirect = await db_session.get(AuthRedirectDB, token)
    assert auth_redirect is not None
    assert auth_redirect.return_to == TEST_RETURN_TO


@pytest.mark.parametrize(
    "return_to",
    [
        "/relative/path",
        "ftp://frontend.test/path",
        "http://untrusted.test/path",
        "http://user@frontend.test/path",
        "http://frontend.test:not-a-port/path",
    ],
    ids=["relative", "unsupported-scheme", "untrusted-origin", "userinfo", "invalid-port"],
)
async def test__login_rejects_invalid_return_urls(client: AsyncClient, return_to: str):
    client.cookies.clear()

    response = await client.get("/auth/login", params={"return_to": return_to})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert COOKIE_AUTH_REDIRECT_KEY not in client.cookies


async def test__login_enforces_production_https_rules(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "environment", "prod")
    monkeypatch.setattr(
        settings,
        "allowed_return_origins",
        ["http://frontend.test", "https://frontend.test", "https://frontend.test:444"],
    )

    insecure_response = await client.get(
        "/auth/login",
        params={"return_to": "http://frontend.test/login-complete"},
    )
    nonstandard_port_response = await client.get(
        "/auth/login",
        params={"return_to": "https://frontend.test:444/login-complete"},
    )
    valid_response = await client.get(
        "/auth/login",
        params={"return_to": "https://frontend.test/login-complete"},
    )

    assert insecure_response.status_code == HTTPStatus.BAD_REQUEST
    assert nonstandard_port_response.status_code == HTTPStatus.BAD_REQUEST
    assert valid_response.status_code == HTTPStatus.TEMPORARY_REDIRECT


async def test__validate_requires_auth_redirect_cookie(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    client.cookies.clear()
    cas_client = _mock_cas_response(monkeypatch, _successful_cas_xml())

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    cas_client.get.assert_not_awaited()


async def test__validate_rejects_unknown_auth_redirect(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    client.cookies.set(COOKIE_AUTH_REDIRECT_KEY, "x" * 43)
    cas_client = _mock_cas_response(monkeypatch, _successful_cas_xml())

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    cas_client.get.assert_not_awaited()


async def test__validate_rejects_expired_auth_redirect(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    _, token = await _start_login(client)
    await db_session.execute(
        sqlalchemy.update(AuthRedirectDB)
        .where(AuthRedirectDB.id == token)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db_session.commit()
    cas_client = _mock_cas_response(monkeypatch, _successful_cas_xml())

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    cas_client.get.assert_not_awaited()


async def test__validate_returns_unauthorized_for_failed_cas_ticket(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    _, token = await _start_login(client)
    cas_client = _mock_cas_response(monkeypatch, _failed_cas_xml())

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert COOKIE_SESSION_KEY not in client.cookies
    assert client.cookies.get(COOKIE_AUTH_REDIRECT_KEY) == token
    assert await db_session.get(AuthRedirectDB, token) is not None
    cas_client.get.assert_awaited_once()


async def test__validate_returns_bad_gateway_for_cas_http_error(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    await _start_login(client)
    cas_client = _mock_cas_response(monkeypatch, "CAS unavailable", HTTPStatus.SERVICE_UNAVAILABLE)

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert COOKIE_SESSION_KEY not in client.cookies
    cas_client.get.assert_awaited_once()


async def test__validate_returns_bad_gateway_for_cas_connection_error(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    await _start_login(client)
    cas_client = AsyncMock(spec=AsyncClient)
    cas_client.get = AsyncMock(
        side_effect=httpx.ConnectError(
            "connection failed",
            request=Request("GET", CAS_VALIDATE_URL),
        )
    )
    monkeypatch.setattr(app.state, "http_client", cas_client, raising=False)

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert COOKIE_SESSION_KEY not in client.cookies
    cas_client.get.assert_awaited_once()


@pytest.mark.parametrize(
    "cas_xml",
    [
        "<not-xml",
        "<root />",
        '<cas:serviceResponse xmlns:cas="http://www.yale.edu/tp/cas"><cas:authenticationSuccess /></cas:serviceResponse>',
    ],
    ids=["malformed-xml", "missing-service-response", "missing-user"],
)
async def test__validate_returns_bad_gateway_for_malformed_cas_response(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    cas_xml: str,
):
    await _start_login(client)
    _mock_cas_response(monkeypatch, cas_xml)

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert COOKIE_SESSION_KEY not in client.cookies


async def test__validate_creates_session_returns_history_scrubbing_page_and_prevents_replay(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    client.cookies.clear()
    _, token = await _start_login(client)
    cas_client = _mock_cas_response(monkeypatch, _successful_cas_xml())

    response = await client.get("/auth/validate", params={"ticket": TEST_TICKET})

    assert response.status_code == HTTPStatus.OK
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    history_replacement = 'history.replaceState(null, "", "/");'
    location_replacement = f"window.location.replace({json.dumps(TEST_RETURN_TO)});"
    assert history_replacement in response.text
    assert location_replacement in response.text
    assert response.text.index(history_replacement) < response.text.index(location_replacement)
    assert TEST_TICKET not in response.text
    assert COOKIE_AUTH_REDIRECT_KEY not in client.cookies
    assert COOKIE_SESSION_KEY in client.cookies

    session_id = client.cookies[COOKIE_SESSION_KEY]
    assert len(session_id) == 43
    session_cookie = next(
        cookie for cookie in response.headers.get_list("set-cookie") if cookie.startswith(f"{COOKIE_SESSION_KEY}=")
    )
    assert f"Max-Age={COOKIE_MAX_AGE}" in session_cookie
    assert "HttpOnly" in session_cookie
    assert f"SameSite={COOKIE_SAMESITE}" in session_cookie

    validate_url = urlsplit(cas_client.get.await_args.args[0])
    cas_validate_url = urlsplit(CAS_VALIDATE_URL)
    assert (validate_url.scheme, validate_url.netloc, validate_url.path) == (
        cas_validate_url.scheme,
        cas_validate_url.netloc,
        cas_validate_url.path,
    )
    assert parse_qs(validate_url.query) == {
        "service": [f"{TEST_APP_URL}/auth/validate"],
        "ticket": [TEST_TICKET],
    }

    db_session.expire_all()
    assert await db_session.get(AuthRedirectDB, token) is None
    user_session = await db_session.get(UserSessionDB, _session_hash(session_id))
    assert user_session is not None
    assert user_session.computing_id == TEST_COMPUTING_ID
    assert user_session.expires_at > datetime.now(UTC)

    user_response = await client.get("/auth/user")
    assert user_response.status_code == HTTPStatus.OK
    assert user_response.json() == {
        "computing_id": TEST_COMPUTING_ID,
        "roles": [],
    }

    verify_response = await client.get("/auth/verify")
    assert verify_response.status_code == HTTPStatus.NO_CONTENT
    assert verify_response.content == b""

    client.cookies.set(COOKIE_AUTH_REDIRECT_KEY, token)
    replay_response = await client.get("/auth/validate", params={"ticket": "ST-replay"})
    assert replay_response.status_code == HTTPStatus.BAD_REQUEST
    cas_client.get.assert_awaited_once()


@pytest.mark.parametrize("path", ["/auth/user", "/auth/verify"])
async def test__authenticated_endpoints_reject_missing_session(client: AsyncClient, path: str):
    client.cookies.clear()

    response = await client.get(path)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize("path", ["/auth/user", "/auth/verify"])
async def test__authenticated_endpoints_reject_expired_session(
    client: AsyncClient,
    db_session: AsyncSession,
    path: str,
):
    session_id = f"expired-{path.rsplit('/', maxsplit=1)[-1]}"
    session_hash = await _create_logged_in_client(db_session, client, session_id, "expired")
    await db_session.execute(
        sqlalchemy.update(UserSessionDB)
        .where(UserSessionDB.session_hash == session_hash)
        .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    await db_session.commit()

    response = await client.get(path)

    assert response.status_code == HTTPStatus.UNAUTHORIZED


async def test__user_returns_assigned_roles(client: AsyncClient, db_session: AsyncSession):
    computing_id = "user-info"
    await _create_logged_in_client(
        db_session,
        client,
        "user-info-session",
        computing_id,
        UserRole.EXEC,
    )
    db_session.add(
        SiteUserRoleDB(
            computing_id=computing_id,
            role=UserRole.USER,
            added_by=None,
        )
    )
    await db_session.commit()

    response = await client.get("/auth/user")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["computing_id"] == computing_id
    assert set(response.json()["roles"]) == {
        UserRole.EXEC.value,
        UserRole.USER.value,
    }
    assert set(response.json()) == {"computing_id", "roles"}


async def test__logout_deletes_session_cookie_and_database_row(client: AsyncClient, db_session: AsyncSession):
    session_id = "logout-session"
    session_hash = await _create_logged_in_client(db_session, client, session_id, "logout")

    response = await client.post("/auth/logout")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert response.content == b""
    assert COOKIE_SESSION_KEY not in client.cookies
    assert f"{COOKIE_SESSION_KEY}=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]
    db_session.expire_all()
    assert await db_session.get(UserSessionDB, session_hash) is None

    second_response = await client.post("/auth/logout")
    assert second_response.status_code == HTTPStatus.NO_CONTENT


async def test__verify_without_required_role_only_checks_session(
    client: AsyncClient,
    db_session: AsyncSession,
):
    await _create_logged_in_client(db_session, client, "verify-session", "verify")

    response = await client.get("/auth/verify")
    role_response = await client.get(
        "/auth/verify",
        headers={"X-Required-Role": UserRole.USER.value},
    )
    invalid_role_response = await client.get(
        "/auth/verify",
        headers={"X-Required-Role": "super-admin"},
    )

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert role_response.status_code == HTTPStatus.FORBIDDEN
    assert invalid_role_response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


@pytest.mark.parametrize(
    ("user_role", "required_role", "expected_status"),
    [
        (UserRole.ADMIN, UserRole.ADMIN, HTTPStatus.NO_CONTENT),
        (UserRole.ADMIN, UserRole.EXEC, HTTPStatus.NO_CONTENT),
        (UserRole.ADMIN, UserRole.USER, HTTPStatus.NO_CONTENT),
        (UserRole.EXEC, UserRole.ADMIN, HTTPStatus.FORBIDDEN),
        (UserRole.EXEC, UserRole.EXEC, HTTPStatus.NO_CONTENT),
        (UserRole.EXEC, UserRole.USER, HTTPStatus.NO_CONTENT),
        (UserRole.USER, UserRole.ADMIN, HTTPStatus.FORBIDDEN),
        (UserRole.USER, UserRole.EXEC, HTTPStatus.FORBIDDEN),
        (UserRole.USER, UserRole.USER, HTTPStatus.NO_CONTENT),
    ],
)
async def test__verify_enforces_role_hierarchy(
    client: AsyncClient,
    db_session: AsyncSession,
    user_role: UserRole,
    required_role: UserRole,
    expected_status: HTTPStatus,
):
    computing_id = f"r{user_role.value[0]}{required_role.value[0]}"
    await _create_logged_in_client(
        db_session,
        client,
        f"role-session-{computing_id}",
        computing_id,
        user_role,
    )

    response = await client.get(
        "/auth/verify",
        headers={"X-Required-Role": required_role.value},
    )

    assert response.status_code == expected_status
