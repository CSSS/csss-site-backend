import base64
import logging
import os
import urllib.parse

import requests  # TODO: make this async
import xmltodict
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

import database
from auth import crud
from constants import FRONTEND_ROOT_URL

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
    redirect_path: str,
    redirect_fragment: str,
    ticket: str,
    db_session: database.DBSession,
    background_tasks: BackgroundTasks,
):
    # verify the ticket is valid
    service = urllib.parse.quote(f"{FRONTEND_ROOT_URL}/api/auth/login?redirect_path={redirect_path}&redirect_fragment={redirect_fragment}")
    service_validate_url = f"https://cas.sfu.ca/cas/serviceValidate?service={service}&ticket={ticket}"
    cas_response = xmltodict.parse(requests.get(service_validate_url).text)

    if "cas:authenticationFailure" in cas_response["cas:serviceResponse"]:
        _logger.info(f"User failed to login, with response {cas_response}")
        raise HTTPException(status_code=401, detail="authentication error, ticket likely invalid")

    else:
        session_id = generate_session_id_b64(256)
        computing_id = cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]["cas:user"]

        await crud.create_user_session(db_session, session_id, computing_id)
        await db_session.commit()

        # clean old sessions after sending the response
        background_tasks.add_task(crud.task_clean_expired_user_sessions, db_session)

        response = RedirectResponse(FRONTEND_ROOT_URL + redirect_path + "#" + redirect_fragment)
        response.set_cookie(
            key="session_id", value=session_id
        )  # this overwrites any past, possibly invalid, session_id
        return response


@router.get(
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


@router.get(
    "/user",
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

    user_info = await crud.update_site_user(db_session, session_id, profile_picture_url)
    if user_info is None:
        raise HTTPException(status_code=401, detail="Could not find user with session_id, please log in")

    return JSONResponse(user_info.serializable_dict())
