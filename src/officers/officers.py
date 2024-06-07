import database

import auth.crud
from src.permission.types import OfficerPrivateInfo

from fastapi import APIRouter, Request


router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)


@router.get(
    "/current",
    description="Get information about all the officers. More information is given if you're authenticated & have permissions.",
)
async def current_officers(
    request: Request,  # NOTE: these are the request headers
    db_session: database.DBSession,
):
    # TODO: get info about officers that satisfy is_active
    # If there are more than 1 active for a certain thing, log it to a file

    # determine if the user has access to this private data
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        has_private_access = False
    else:
        computing_id = auth.crud.get_computing_id(db_session, session_id)
        has_private_access = OfficerPrivateInfo.user_has_permission(db_session, computing_id)

    # TODO: question?
    if has_private_access:
        pass
    else:
        pass

    # TODO: use a logging library that enables logging to separate files as modules, so we
    # can have an officers module, etc...

    # TODO: where are root level exceptions raised to?

    # It will also be helpful to have a hook in the logging library to send an email to
    # csss-sysadmin@sfu.ca & (csss-webmaster@sfu.ca)? when errors or warnings are logged

    return {"officers": "no current officers yet!"}


# TODO: test this error afterwards
@router.get("/please_error", description="Raises an error & should send an email to the sysadmin")
async def raise_error():
    raise ValueError("This is an error, you're welcome")


@router.get(
    "/past",
    description="Information from past exec terms. If year is not included, all years will be returned. If semester is not included, all semesters that year will be returned. If semester is given, but year is not, return all years and all semesters.",
)
async def past_officers():
    return {"officers": "none"}


@router.post(
    "/enter_info",
    description="After elections, officer computing ids are input into our system. If you have been elected as a new officer, you may authenticate with SFU CAS, then input your information & the valid token for us.",
)
async def enter_info():
    # provide data as json, the response determines if data was inserted into the database or not

    # the current user can only input the info for another user if they have permissions

    return {}


"""
@router.get(
    "/my_info",
    description="Get info about whether you are still an executive or not / what your position is.",
)
async def my_info():
    return {}
"""


@router.post(
    "/new",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Updates the system with a new officer, and enables the user to login to the system to input their information.",
)
async def add_new_officer():
    return {}


@router.post(
    "/remove",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Removes the officer from the system entirely. BE CAREFUL WITH THIS OPTION aaaaaaaaaaaaaaaaaa.",
)
async def remove_officer():
    return {}


@router.post(
    "/update",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Modify the stored info of an existing officer.",
)
async def update_officer():
    return {}
