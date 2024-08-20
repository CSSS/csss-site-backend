import base64
import logging
import os
import urllib.parse

import database
import requests  # TODO: make this async
import xmltodict
from auth import crud
from auth.types import SessionType
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

    elif "cas:authenticationSuccess" in cas_response["cas:serviceResponse"]:
        session_id = generate_session_id_b64(256)
        computing_id = cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]["cas:user"]

        # NOTE: it is the frontend's job to pass the correct authentication reuqest to CAS, otherwise we
        # will only be able to give a user the "sfu" session_type (least privileged)
        if "cas:maillist" in cas_response["cas:serviceResponse"]:
            # maillist
            # TODO: (ASK SFU IT) can alumni be in the cmpt-students maillist?
            if cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]["cas:maillist"] == "cmpt-students":
                session_type = SessionType.CSSS_MEMBER
            else:
                raise HTTPException(status_code=500, details="malformed authentication response; this is an SFU CAS error")
        elif "cas:authtype" in cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]:
            # sfu, alumni, faculty, student
            session_type = cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]["cas:authtype"]
            if session_type not in SessionType.value_list():
                raise HTTPException(status_code=500, detail=f"unexpected session type from SFU CAS of {session_type}")
        else:
            raise HTTPException(status_code=500, detail="malformed authentication response; this is an SFU CAS error")

        await crud.create_user_session(db_session, session_id, computing_id, session_type)
        await db_session.commit()

        # clean old sessions after sending the response
        background_tasks.add_task(crud.task_clean_expired_user_sessions, db_session)

        response = RedirectResponse(next_url)
        response.set_cookie(
            key="session_id", value=session_id
        )  # this overwrites any past, possibly invalid, session_id
        return response

    else:
        raise HTTPException(status_code=500, detail="malformed authentication response; this is an SFU CAS error")


@router.get(
    "/check",
    description="Check if the current user is logged in based on session_id from cookies",
)
async def check_authentication(
    # the request headers
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get("session_id", None)

    if session_id:
        await crud.task_clean_expired_user_sessions(db_session)
        response_dict = await crud.check_user_session(db_session, session_id)
    else:
        response_dict = {"is_valid": False}

    return JSONResponse(response_dict)


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

