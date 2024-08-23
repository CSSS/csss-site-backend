import base64
import logging
import os
import urllib.parse

import database
import requests  # TODO: make this async
import xmltodict
from auth import crud
from constants import root_ip_address
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

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


# NOTE: logging in a second time invaldiates the last session_id
@router.get(
    "/login",
    description="Login to the sfucsss.org. Must redirect to this endpoint from SFU's cas authentication service for correct parameters",
)
async def login_user(
    next_url: str,
    ticket: str,
    db_session: database.DBSession,
    background_tasks: BackgroundTasks,
):
    # TODO: test this
    if not next_url.startswith(root_ip_address):
        raise HTTPException(status_code=400, detail=f"invalid next_url={next_url}, must be a page of our site")

    # verify the ticket is valid
    url = (
        f"https://cas.sfu.ca/cas/serviceValidate?service={urllib.parse.quote(root_ip_address)}"
        f"/api/auth/login%3Fnext_url%3D{urllib.parse.quote(next_url)}&ticket={ticket}"
    )
    cas_response = xmltodict.parse(requests.get(url).text)

    if "cas:authenticationFailure" in cas_response["cas:serviceResponse"]:
        _logger.info(f"User failed to login, with response {cas_response}")
        raise HTTPException(status_code=400, detail="authentication error, ticket likely invalid")

    else:
        session_id = generate_session_id_b64(256)
        computing_id = cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]["cas:user"]

        await crud.create_user_session(db_session, session_id, computing_id)
        await db_session.commit()

        # clean old sessions after sending the response
        background_tasks.add_task(crud.task_clean_expired_user_sessions, db_session)

        response = RedirectResponse(next_url)
        response.set_cookie(
            key="session_id", value=session_id
        )  # this overwrites any past, possibly invalid, session_id
        return response


# TODO: deprecate this when possible
@router.get(
    "/check",
    description="Check if the current user is logged in based on session_id from cookies",
)
async def check_authentication(
    request: Request,  # NOTE: these are the request headers
    db_session: database.DBSession,
):
    session_id = request.cookies.get("session_id", None)

    if session_id:
        await crud.task_clean_expired_user_sessions(db_session)
        response_dict = await crud.check_user_session(db_session, session_id)
    else:
        response_dict = {"is_valid": False}

    return JSONResponse(response_dict)


@router.get(
    "/info",
    description="Get info about the current user. Only accessible by that user",
)
async def get_info(
    request: Request,
    db_session: database.DBSession,
):
    """
    Currently this endpoint only returns the info stored in tables in the auth module.
    """
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="User must be authenticated to get their info")

    user_info = await crud.user_info(db_session, session_id)
    if user_info is None:
        raise HTTPException(status_code=500, detail="Could not find user with session_id")

    return JSONResponse(user_info)


@router.post(
    "/logout",
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
