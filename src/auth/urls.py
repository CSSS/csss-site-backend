import base64
import logging
import os
import urllib.parse
from typing import Literal

import requests  # TODO: make this async
import xmltodict
from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

import database
from auth import crud
from auth.models import LoginBodyModel
from constants import IS_PROD
from utils.shared_models import DetailModel

_logger = logging.getLogger(__name__)

# ----------------------- #
# utils


# ex: rsa4096 is 512 bytes
def generate_session_id_b64(num_bytes: int) -> str:
    return base64.b64encode(os.urandom(num_bytes)).decode("utf-8")


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
    response_model=None,
    responses={
        307: { "description": "Successful validation, with redirect" },
        400: { "description": "Origin is missing.", "model": DetailModel },
        401: { "description": "Failed to validate ticket with SFU's CAS", "model": DetailModel }
    },
    operation_id="login",
)
async def login_user(
    request: Request,
    db_session: database.DBSession,
    background_tasks: BackgroundTasks,
    body: LoginBodyModel
):
    # verify the ticket is valid
    service_url = body.service
    service = urllib.parse.quote(service_url)
    service_validate_url = f"https://cas.sfu.ca/cas/serviceValidate?service={service}&ticket={body.ticket}"
    cas_response = xmltodict.parse(requests.get(service_validate_url).text)

    if "cas:authenticationFailure" in cas_response["cas:serviceResponse"]:
        _logger.info(f"User failed to login, with response {cas_response}")
        raise HTTPException(status_code=401, detail="authentication error")
    else:
        session_id = generate_session_id_b64(256)
        computing_id = cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]["cas:user"]

        await crud.create_user_session(db_session, session_id, computing_id)
        await db_session.commit()

        # clean old sessions after sending the response
        background_tasks.add_task(crud.task_clean_expired_user_sessions, db_session)

        if body.redirect_url:
            origin = request.headers.get("origin")
            if origin:
                response = RedirectResponse(origin + body.redirect_url)
            else:
                raise HTTPException(status_code=400, detail="bad origin")
        else:
            response = Response()

        response.set_cookie(
            key="session_id",
            value=session_id,
            secure=IS_PROD,
            httponly=True,
            samesite=None if IS_PROD else "lax",
            domain=".sfucsss.org" if IS_PROD else None
        )  # this overwrites any past, possibly invalid, session_id
        return response


@router.get(
    "/logout",
    operation_id="logout",
    description="Logs out the current user by invalidating the session_id cookie",
)
async def logout_user(
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get("session_id", None)

    if session_id:
        await crud.remove_user_session(db_session, session_id)
        await db_session.commit()
        response_dict = {"message": "logout successful"}
    else:
        response_dict = {"message": "user was not logged in"}

    response = JSONResponse(response_dict)
    response.delete_cookie(key="session_id")
    return response


@router.get(
    "/user",
    operation_id="get_user",
    description="Get info about the current user. Only accessible by that user",
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
        raise HTTPException(status_code=401, detail="User must be authenticated to get their info")

    user_info = await crud.get_site_user(db_session, session_id)
    if user_info is None:
        raise HTTPException(status_code=401, detail="Could not find user with session_id, please log in")

    return JSONResponse(user_info.serializable_dict())


@router.patch(
    "/user",
    operation_id="update_user",
    description="Update information for the currently logged in user. Only accessible by that user",
)
async def update_user(
    profile_picture_url: str,
    request: Request,
    db_session: database.DBSession,
):
    """
    Returns the info stored in the site_user table in the auth module, if the user is logged in.
    """
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="User must be authenticated to get their info")

    ok = await crud.update_site_user(db_session, session_id, profile_picture_url)
    await db_session.commit()
    if not ok:
        raise HTTPException(status_code=401, detail="Could not find user with session_id, please log in")

    return PlainTextResponse("ok")
