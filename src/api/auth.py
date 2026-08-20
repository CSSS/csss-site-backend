from fastapi import Depends, HTTPException, Request, status

from config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def require_trusted_origin(request: Request) -> None:
    if request.method in SAFE_METHODS:
        return

    origin = request.headers.get("Origin")

    if origin not in settings.allowed_origins:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid request",
        )
