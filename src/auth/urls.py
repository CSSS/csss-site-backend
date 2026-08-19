import base64
import logging
import os
from datetime import UTC, datetime
from urllib.parse import quote, urlencode, urlsplit

import httpx
import xmltodict
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

import database
from auth import crud
from auth.constants import (
    CAS_LOGIN_URL,
    CAS_VALIDATE_URL,
    COOKIE_AUTH_REDIRECT_KEY,
    COOKIE_MAX_AGE,
    COOKIE_PATH,
    COOKIE_SAMESITE,
    COOKIE_SESSION_KEY,
    REDIRECT_TTL,
)
from auth.models import UserInfo
from config import settings
from dependencies import LoggedInUser, logged_in_user
from utils.permissions import UserRole, is_user_role, roles_satisfy
from utils.shared_models import DetailModel, MessageModel

_logger = logging.getLogger(__name__)

# ----------------------- #
# utils


def _generate_session_id() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")


def _validate_return_to_url(return_to: str) -> None:
    try:
        url = urlsplit(return_to)
        port = url.port
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return URL is invalid") from None

    if not url.scheme or not url.hostname:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return URL is invalid")

    if url.username is not None or url.password is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return URL is invalid")

    if settings.environment == "prod":
        if url.scheme != "https":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return URL must use HTTPS")

        if port not in (None, 443):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return URL must use default HTTPS port")
    elif url.scheme not in ("http", "https"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return URL must use HTTP or HTTPS")

    if port is None:
        if url.scheme == "https":
            port = 443
        elif url.scheme == "http":
            port = 80

    origin = f"{url.scheme}://{url.hostname}"

    if (url.scheme == "https" and port != 443) or (url.scheme == "http" and port != 80):
        origin += f":{port}"

    if origin not in settings.allowed_return_origins:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Return URL is not allowed")


def __make_service_url() -> str:
    return f"{settings.app_url}/auth/validate"


# ----------------------- #
# api

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.get(
    "/login",
    description="Start a log in attempt and redirect to CAS.",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={
        307: {"description": "Redirect to SFU CAS"},
        400: {"description": "Invalid redirect URL", "model": DetailModel},
    },
    operation_id="login",
)
async def login(db_session: database.DBSession, request: Request, return_to: str | None = None):
    if return_to is None:
        return_to = request.headers.get("X-Original-URL")

    if return_to is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing return URL")

    _validate_return_to_url(return_to)

    # TODO: Create a CRON job that clears the table periodically
    token = _generate_session_id()

    crud.create_auth_redirect(db_session, token, return_to)
    await db_session.commit()

    cas_url = f"{CAS_LOGIN_URL}?{urlencode({'service': __make_service_url()})}"

    response = RedirectResponse(cas_url)

    response.set_cookie(
        key=COOKIE_AUTH_REDIRECT_KEY,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        domain=settings.cookie_domain,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=REDIRECT_TTL,
    )

    return response


@router.get(
    "/validate",
    description="Validates the ticket by contacting SFU's CAS.",
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    responses={
        307: {"description": "Successfully validated with SFU's CAS"},
        400: {"description": "Login attempt invalid", "model": DetailModel},
        401: {"description": "Failed to validate ticket with SFU's CAS", "model": DetailModel},
        502: {"description": "Failed to connect to SFU's CAS", "model": DetailModel},
    },
    operation_id="validate",
)
async def validate_ticket(
    request: Request, db_session: database.DBSession, background_tasks: BackgroundTasks, ticket: str
):
    token = request.cookies.get(COOKIE_AUTH_REDIRECT_KEY)

    if token is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Missing authentication token")

    auth_redirect = await crud.get_auth_redirect(db_session, token)
    if not auth_redirect or auth_redirect.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid login attempt")
    await db_session.rollback()

    # verify the ticket is valid
    service_validate_url = f"{CAS_VALIDATE_URL}?{urlencode({'service': __make_service_url(), 'ticket': ticket})}"
    client = request.app.state.http_client

    try:
        auth_response = await client.get(service_validate_url)
        auth_response.raise_for_status()
    except httpx.HTTPStatusError as e:
        _logger.warning("Cas returned HTTP %s", e.response.status_code)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Authentication error") from None
    except httpx.RequestError as e:
        _logger.warning("Cas request failed: %s", type(e).__name__)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Authentication error") from None

    try:
        cas_response = xmltodict.parse(auth_response.text)
    except Exception:
        _logger.exception("CAS response malformed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Authentication error") from None

    service_response = cas_response.get("cas:serviceResponse")
    if not isinstance(service_response, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Authentication error")

    if "cas:authenticationFailure" in service_response:
        _logger.warning("CAS login failure")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication error")

    auth_success = service_response.get("cas:authenticationSuccess")
    if not isinstance(auth_success, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="authentication error")

    # Create session
    computing_id = auth_success.get("cas:user")
    if not isinstance(computing_id, str) or not computing_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="authentication error")

    # clean old sessions after sending the response
    # TODO: Convert this to a daily CRON job
    background_tasks.add_task(crud.task_clean_expired_user_sessions, db_session)

    # Delete auth redirect record and cookie
    return_to = await crud.delete_auth_redirect(db_session, token)
    if return_to is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid login attempt")

    response = RedirectResponse(return_to)
    response.delete_cookie(key=COOKIE_AUTH_REDIRECT_KEY, domain=settings.cookie_domain, path=COOKIE_PATH)

    # Construct the response
    session_id = _generate_session_id()
    response.set_cookie(
        key=COOKIE_SESSION_KEY,
        value=session_id,
        secure=settings.cookie_secure,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        domain=settings.cookie_domain,
        max_age=COOKIE_MAX_AGE,
        path=COOKIE_PATH,
    )  # this overwrites any past, possibly invalid, session_id
    await crud.create_user_session(db_session, session_id, computing_id)
    await db_session.commit()
    return response


@router.post(
    "/logout",
    description="Logs out the current user by deleting the session data. Does not log out of CAS.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successfully logged out."},
    },
    operation_id="logout",
)
async def logout_user(
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get(COOKIE_SESSION_KEY)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=COOKIE_SESSION_KEY,
        secure=settings.cookie_secure,
        domain=settings.cookie_domain,
        path=COOKIE_PATH,
    )

    if not session_id:
        return response

    await crud.remove_user_session_by_id(db_session, session_id)
    await db_session.commit()
    return response


@router.get(
    "/user",
    description="Get info about the current user.",
    response_model=UserInfo,
    responses={
        401: {"description": "Not logged in."},
    },
    operation_id="get_user",
)
async def get_user(
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get(COOKIE_SESSION_KEY)
    if session_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_info = await crud.get_site_user(db_session, session_id)
    if user_info is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user_info


@router.get(
    "/verify",
    description="Verify the user's session exists.",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def verify_session(
    db_session: database.DBSession,
    computing_id: LoggedInUser,
    x_required_role: str | None = Header(default=None, alias="X-Required-Role"),
):
    if x_required_role is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    try:
        required_role = UserRole(x_required_role)
    except ValueError:
        # If you hit this then check the Nginx config
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Invalid required role") from None

    if not (await roles_satisfy(db_session, computing_id, required_role)):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User does not have the required role")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
