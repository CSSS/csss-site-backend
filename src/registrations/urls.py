from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

import database
import elections.crud
import nominees.crud
import registrations.crud
from elections.models import (
    ElectionStatusEnum,
)
from officers.constants import OfficerPositionEnum
from registrations.models import (
    NomineeApplicationModel,
    NomineeApplicationParams,
    NomineeApplicationUpdateParams,
)
from registrations.tables import NomineeApplication
from utils.shared_models import DetailModel, SuccessResponse
from utils.urls import admin_or_raise, logged_in_or_raise, slugify

router = APIRouter(
    prefix="/registration",
    tags=["registration"],
)

@router.get(
    "/{election_name:str}",
    description="get all the registrations of a single election",
    response_model=list[NomineeApplicationModel],
    responses={
        401: { "description": "Not logged in", "model": DetailModel },
        404: { "description": "Election with slug does not exist", "model": DetailModel }
     },
    operation_id="get_election_registrations"
)
async def get_election_registrations(
    request: Request,
    db_session: database.DBSession,
    election_name: str
):
    _, computing_id = await logged_in_or_raise(request, db_session)

    slugified_name = slugify(election_name)
    if await elections.crud.get_election(db_session, slugified_name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    registration_list = await registrations.crud.get_all_registrations_of_user(db_session, computing_id, slugified_name)
    if registration_list is None:
        return JSONResponse([])
    return JSONResponse([
        item.serialize() for item in registration_list
    ])

@router.post(
    "/{election_name:str}",
    description="Register for a specific position in this election, but doesn't set a speech. Returns the created entry.",
    response_model=NomineeApplicationModel,
    responses={
        400: { "description": "Bad request", "model": DetailModel },
        401: { "description": "Not logged in", "model": DetailModel },
        403: { "description": "Not an admin", "model": DetailModel },
        404: { "description": "No election found", "model": DetailModel },
    },
    operation_id="register"
)
async def register_in_election(
    request: Request,
    db_session: database.DBSession,
    body: NomineeApplicationParams,
    election_name: str
):
    await admin_or_raise(request, db_session)

    if body.position not in OfficerPositionEnum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {body.position}"
        )

    if await nominees.crud.get_nominee_info(db_session, body.computing_id) is None:
        # ensure that the user has a nominee info entry before allowing registration to occur.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="must have submitted nominee info before registering"
        )

    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    if body.position not in election.available_positions:
        # NOTE: We only restrict creating a registration for a position that doesn't exist,
        # not updating or deleting one
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.position} is not available to register for in this election"
        )

    if election.status(datetime.now()) != ElectionStatusEnum.NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registrations can only be made during the nomination period"
        )

    if await registrations.crud.get_all_registrations_of_user(db_session, body.computing_id, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="person is already registered in this election"
        )

    # TODO: associate specific election officers with specific election, then don't
    # allow any election officer running an election to register for it
    await registrations.crud.add_registration(db_session, NomineeApplication(
        computing_id=body.computing_id,
        nominee_election=slugified_name,
        position=body.position,
        speech=None
    ))
    await db_session.commit()

    registrant = await registrations.crud.get_one_registration_in_election(
        db_session, body.computing_id, slugified_name, body.position
    )
    if not registrant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to find new registrant"
        )
    return registrant

@router.patch(
    "/{election_name:str}/{position:str}/{computing_id:str}",
    description="update the application of a specific registrant and return the changed entry",
    response_model=NomineeApplicationModel,
    responses={
        400: { "description": "Bad request", "model": DetailModel },
        401: { "description": "Not logged in", "model": DetailModel },
        403: { "description": "Not an admin", "model": DetailModel },
        404: { "description": "No election found", "model": DetailModel },
    },
    operation_id="update_registration"
)
async def update_registration(
    request: Request,
    db_session: database.DBSession,
    body: NomineeApplicationUpdateParams,
    election_name: str,
    computing_id: str,
    position: OfficerPositionEnum
):
    await admin_or_raise(request, db_session)

    if body.position not in OfficerPositionEnum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {body.position}"
    )

    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    # self updates can only be done during nomination period. Officer updates can be done whenever
    if election.status(datetime.now()) != ElectionStatusEnum.NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="speeches can only be updated during the nomination period"
        )

    registration = await registrations.crud.get_one_registration_in_election(db_session, computing_id, slugified_name, position)
    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no registration record found"
        )

    registration.update_from_params(body)

    await registrations.crud.update_registration(db_session, registration)
    await db_session.commit()

    registrant = await registrations.crud.get_one_registration_in_election(
        db_session, registration.computing_id, slugified_name, registration.position
    )
    if not registrant:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to find changed registrant"
        )
    return registrant

@router.delete(
    "/{election_name:str}/{position:str}/{computing_id:str}",
    description="delete the registration of a person",
    response_model=SuccessResponse,
    responses={
        400: { "description": "Bad request", "model": DetailModel },
        401: { "description": "Not logged in", "model": DetailModel },
        403: { "description": "Not an admin", "model": DetailModel },
        404: { "description": "No election or registrant found", "model": DetailModel },
    },
    operation_id="delete_registration"
)
async def delete_registration(
    request: Request,
    db_session: database.DBSession,
    election_name: str,
    position: OfficerPositionEnum,
    computing_id: str
):
    await admin_or_raise(request, db_session)

    if position not in OfficerPositionEnum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid position {position}"
        )

    slugified_name = slugify(election_name)
    election = await elections.crud.get_election(db_session, slugified_name)
    if election is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"election with slug {slugified_name} does not exist"
        )

    if election.status(datetime.now()) != ElectionStatusEnum.NOMINATIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="registration can only be revoked during the nomination period"
        )

    if not await registrations.crud.get_all_registrations_of_user(db_session, computing_id, slugified_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{computing_id} was not registered in election {slugified_name} for {position}"
        )

    await registrations.crud.delete_registration(db_session, computing_id, slugified_name, position)
    await db_session.commit()
    old_election = await registrations.crud.get_one_registration_in_election(db_session, computing_id, slugified_name, position)
    return JSONResponse({"success": old_election is None})

