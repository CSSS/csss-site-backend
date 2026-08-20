import pytest
from fastapi import HTTPException, Request, status

from api.auth import SAFE_METHODS, require_trusted_origin
from config import settings

pytestmark = pytest.mark.unit

TRUSTED_ORIGIN = "https://frontend.test"


def make_request(method: str, origin: str | None = None) -> Request:
    headers = [] if origin is None else [(b"origin", origin.encode())]
    return Request({"type": "http", "method": method, "headers": headers})


@pytest.mark.parametrize("method", sorted(SAFE_METHODS))
async def test__safe_methods_do_not_require_an_origin(method: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "allowed_origins", [])

    result = await require_trusted_origin(make_request(method))

    assert result is None


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test__unsafe_methods_accept_a_trusted_origin(method: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "allowed_origins", [TRUSTED_ORIGIN])

    result = await require_trusted_origin(make_request(method, TRUSTED_ORIGIN))

    assert result is None


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "https://untrusted.test",
        f"{TRUSTED_ORIGIN}.untrusted.test",
    ],
    ids=["missing", "untrusted", "trusted-origin-prefix"],
)
async def test__unsafe_methods_reject_an_invalid_origin(origin: str | None, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "allowed_origins", [TRUSTED_ORIGIN])

    with pytest.raises(HTTPException) as exc_info:
        await require_trusted_origin(make_request("POST", origin))

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Invalid request"
