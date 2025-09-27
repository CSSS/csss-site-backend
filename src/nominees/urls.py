from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

import database
import nominees.crud
from nominees.models import (
    NomineeInfoModel,
    NomineeInfoUpdateParams,
)
from nominees.tables import NomineeInfo
from utils.shared_models import DetailModel, SuccessResponse
from utils.urls import admin_or_raise

router = APIRouter(
    prefix="/nominee",
    tags=["nominee"],
)

@router.get(
    "",
    description="Get all nominees",
    response_model=list[NomineeInfoModel],
    responses={
        403: { "description": "need to be an admin", "model": DetailModel }
    },
    operation_id="create_nominee"
)
async def get_all_nominees(
    request: Request,
    db_session: database.DBSession,
):
    # Putting this behind a wall since there is private information here
    await admin_or_raise(request, db_session)
    nominees_list = await nominees.crud.get_all_nominees(db_session)

    return JSONResponse([
        item.serialize() for item in nominees_list
    ])

@router.post(
    "",
    description="Nominee info is always publically tied to election, so be careful!",
    response_model=NomineeInfoModel,
    responses={
        500: { "description": "failed to fetch new nominee", "model": DetailModel }
    },
    operation_id="create_nominee"
)
async def create_nominee(
    request: Request,
    db_session: database.DBSession,
    body: NomineeInfoModel
):
    await admin_or_raise(request, db_session)
    await nominees.crud.create_nominee_info(db_session, NomineeInfo(
        computing_id=body.computing_id,
        full_name=body.full_name,
        linked_in=body.linked_in,
        instagram=body.instagram,
        email=body.email,
        discord_username=body.discord_username,
    ))

    nominee_info = await nominees.crud.get_nominee_info(db_session, body.computing_id)
    if nominee_info is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="couldn't fetch newly created nominee"
        )

    return JSONResponse(nominee_info)

@router.get(
    "/{computing_id:str}",
    description="Nominee info is always publically tied to election, so be careful!",
    response_model=NomineeInfoModel,
    responses={
        404: { "description": "nominee doesn't exist" }
    },
    operation_id="get_nominee"
)
async def get_nominee_info(
    request: Request,
    db_session: database.DBSession,
    computing_id: str
):
    # Putting this one behind the admin wall since it has contact information
    await admin_or_raise(request, db_session)
    nominee_info = await nominees.crud.get_nominee_info(db_session, computing_id)
    if nominee_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="nominee doesn't exist"
        )

    return JSONResponse(nominee_info.serialize())

@router.delete(
    "/{computing_id:str}",
    description="Nominee info is always publically tied to election, so be careful!",
    operation_id="delete_nominee"
)
async def delete_nominee_info(
    request: Request,
    db_session: database.DBSession,
    computing_id: str
):
    await admin_or_raise(request, db_session)
    await nominees.crud.delete_nominee_info(db_session, computing_id)
    await db_session.commit()

@router.patch(
    "/{computing_id:str}",
    description="Will create or update nominee info. Returns an updated copy of their nominee info.",
    response_model=NomineeInfoModel,
    responses={
        500: { "description": "Failed to retrieve updated nominee." }
    },
    operation_id="update_nominee"
)
async def provide_nominee_info(
    request: Request,
    db_session: database.DBSession,
    body: NomineeInfoUpdateParams,
    computing_id: str
):
    # TODO: There needs to be a lot more validation here.
    await admin_or_raise(request, db_session)

    updated_data = {}
    # Only update fields that were provided
    if body.full_name is not None:
        updated_data["full_name"] = body.full_name
    if body.linked_in is not None:
       updated_data["linked_in"] = body.linked_in
    if body.instagram is not None:
        updated_data["instagram"] = body.instagram
    if body.email is not None:
        updated_data["email"] = body.email
    if body.discord_username is not None:
        updated_data["discord_username"] = body.discord_username

    # TODO: Look into using something built into SQLAlchemy/Pydantic for better entry updates
    existing_info = await nominees.crud.get_nominee_info(db_session, computing_id)
    # if not already existing, create it
    if not existing_info:
        # unpack dictionary and expand into NomineeInfo class
        new_nominee_info = NomineeInfo(computing_id=computing_id, **updated_data)
        # create a new nominee
        await nominees.crud.create_nominee_info(db_session, new_nominee_info)
    # else just update the partial data
    else:
        merged_data = {
            "computing_id": computing_id,
            "full_name": existing_info.full_name,
            "linked_in": existing_info.linked_in,
            "instagram": existing_info.instagram,
            "email": existing_info.email,
            "discord_username": existing_info.discord_username,
        }
        #  update the dictionary with new data
        merged_data.update(updated_data)
        updated_nominee_info = NomineeInfo(**merged_data)
        await nominees.crud.update_nominee_info(db_session, updated_nominee_info)

    await db_session.commit()

    nominee_info = await nominees.crud.get_nominee_info(db_session, computing_id)
    if not nominee_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to get updated nominee"
        )
    return JSONResponse(nominee_info.serialize())
