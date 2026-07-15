import secrets
from typing import Annotated

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

kiosk_bearer = HTTPBearer(auto_error=False)
KioskCredentials = Annotated[HTTPAuthorizationCredentials | None, Security(kiosk_bearer)]


async def require_kiosk_auth(credentials: KioskCredentials) -> None:
    if settings.kiosk_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )

    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode("utf-8"),
        settings.kiosk_secret.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid kiosk token",
            headers={"WWW-Authenticate": "Bearer"},
        )
