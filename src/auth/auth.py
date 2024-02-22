import base64, datetime

import crud, database
import requests # TODO: make this async
import urllib.parse

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

import OpenSSL, xmltodict

# ----------------------- #
# utils

# ex: rsa4096 is 512 bytes
def generate_session_id_b64(num_bytes) -> str:
    return base64.b64encode(OpenSSL.rand.bytes(num_bytes)).decode("utf-8")

# ----------------------- #
# api

router = APIRouter(
    prefix="/auth",
    tags=["authentication", "login"],
)

# NOTE: logging in a second time invaldiates the last session_id
@router.get(
    "/",
)
async def authenticate_user(
    next: str, # TODO: ensure next is a valid url? or local to our site or something...
    ticket: str, 
    db_session: database.DBSession,
    background_tasks: BackgroundTasks,
):
    # verify the ticket is valid
    url = "https://cas.sfu.ca/cas/serviceValidate?service={}&ticket={}".format(
        "https%3A%2F%2Fapi.sfucsss.org%3Fnext%3D{}".format(urllib.parse.quote(next)), 
        ticket
    )
    cas_response = xmltodict.parse(requests.get(url))

    if "cas:authenticationFailure" in cas_response["cas:serviceResponse"]:
        raise HTTPException(status_code=400, detail="authentication error, ticket likely invalid")

    else:
        session_id = generate_session_id_b64(256)
        computing_id = cas_response["cas:serviceResponse"]["cas:authenticationSuccess"]["cas:user"]

        await crud.create_user_session(db_session, session_id, computing_id)
        await db_session.commit()
        
        # clean old sessions after sending the response
        background_tasks.add_task(crud.task_clean_expired_user_sessions, db_session)

        response = RedirectResponse(next)
        response.set_cookie(key="session_id", value=session_id) # this overwrites any past, possibly invalid, session_id
        return response

# sfucsss.org/login?next=<current-page>
# https://cas.sfu.ca/cas/login?service=https%3A%2F%2Fsfucsss.org%2Flogin%3Fnext%3D<current-page>
# https%3A%2F%2Fsfucsss.org%2Flogin%3Fnext%3D<current-page>?ticket=...
# <current-page> w/ token in cookies

@router.get(
    "/check",
)
async def check_authentication(
    request: Request, # NOTE: these are the request headers
    db_session: database.DBSession,
):
    session_id = request.cookies["session_id"]
    response_dict = crud.check_session_validity(db_session, session_id)
    return JSONResponse(response_dict)
