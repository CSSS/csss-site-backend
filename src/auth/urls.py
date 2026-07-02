import base64
import logging
import os
import urllib.parse

import xmltodict
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

import database
from auth import crud
from auth.constants import COOKIE_MAX_AGE, COOKIE_SESSION_KEY
from auth.models import LoginBodyParams, SiteUser
from config import settings
from utils.shared_models import DetailModel, MessageModel

_logger = logging.getLogger(__name__)

# ----------------------- #
# utils


def _generate_session_id() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")


# ----------------------- #
# api

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


# NOTE: logging in a second time invalidates the last session_id
@router.post(
    "/login",
    description="Create a login session.",
    response_description="Successfully validated with SFU's CAS",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Failed to validate ticket with SFU's CAS", "model": DetailModel},
        502: {"description": "Failed to validate ticket with SFU's CAS", "model": DetailModel},
        503: {"description": "Authentication not configured", "model": DetailModel},
    },
    operation_id="login",
)
async def login_user(
    request: Request, db_session: database.DBSession, background_tasks: BackgroundTasks, body: LoginBodyParams
):
    # verify the ticket is valid
    service = urllib.parse.quote(body.service)
    ticket = urllib.parse.quote(body.ticket)
    if not settings.auth_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="authentication error")
    service_validate_url = f"{settings.auth_url}?service={service}&ticket={ticket}"
    client = request.app.state.http_client

    try:
        response = await client.get(service_validate_url)
        response.raise_for_status()
        cas_response = xmltodict.parse(response.text)
    except Exception:
        _logger.exception(f"CAS Login failure: service={body.service}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="authentication error") from None

    service_response = cas_response.get("cas:serviceResponse")
    if not isinstance(service_response, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="authentication error")

    if "cas:authenticationFailure" in service_response:
        _logger.info(f"CAS Login failure: service={body.service}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication error")

    auth_success = service_response.get("cas:authenticationSuccess")
    if not isinstance(auth_success, dict):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="authentication error")

    session_id = _generate_session_id()
    computing_id = auth_success.get("cas:user")
    if not isinstance(computing_id, str) or not computing_id:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="authentication error")

    # clean old sessions after sending the response
    # TODO: Convert this to a daily CRON job
    background_tasks.add_task(crud.task_clean_expired_user_sessions, db_session)

    if not settings.frontend_origin:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="authentication error")

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.set_cookie(
        key=COOKIE_SESSION_KEY,
        value=session_id,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
        domain=settings.cookie_domain,
        max_age=COOKIE_MAX_AGE,
    )  # this overwrites any past, possibly invalid, session_id
    await crud.create_user_session(db_session, session_id, computing_id)
    await db_session.commit()
    return response


@router.get(
    "/logout",
    description="Logs out the current user by invalidating the session_id cookie",
    operation_id="logout",
    response_model=MessageModel,
)
async def logout_user(
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get("session_id", None)

    if not session_id:
        response_dict = {"message": "user was not logged in"}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no session provided")

    await crud.remove_user_session(db_session, session_id)
    response_dict = {"message": "logout successful"}
    response = JSONResponse(response_dict)
    response.delete_cookie(
        key=COOKIE_SESSION_KEY,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    await db_session.commit()
    return response


@router.get(
    "/user",
    operation_id="get_user",
    description="Get info about the current user. Only accessible by that user",
    response_model=SiteUser,
    responses={401: {"description": "Not logged in.", "model": DetailModel}},
)
async def get_user(
    request: Request,
    db_session: database.DBSession,
):
    """
    Returns the info stored in the site_user table in the auth module, if the user is logged in.
    """
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user must be authenticated to get their info"
        )

    user_info = await crud.get_site_user(db_session, session_id)
    if user_info is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="could not find user with session_id")

    return user_info
