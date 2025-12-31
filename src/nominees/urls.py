from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

import database
import nominees.crud
from dependencies import perm_election
from nominees.models import (
    Nominee,
    NomineeUpdate,
)
from nominees.tables import NomineeInfoDB
from utils.shared_models import DetailModel

router = APIRouter(
    prefix="/nominee",
    tags=["nominee"],
)


@router.get(
    "",
    description="Get all nominees",
    response_model=list[Nominee],
    responses={403: {"description": "need to be an admin", "model": DetailModel}},
    operation_id="get_all_nominees",
    dependencies=[Depends(perm_election)],
)
async def get_all_nominees(
    db_session: database.DBSession,
):
    # Putting this behind a wall since there is private information here
    nominees_list = await nominees.crud.get_all_nominees(db_session)

    return JSONResponse([item.serialize() for item in nominees_list])


@router.post(
    "",
    description="Nominee info is always publically tied to election, so be careful!",
    response_model=Nominee,
    responses={500: {"description": "failed to fetch new nominee", "model": DetailModel}},
    operation_id="create_nominee",
    dependencies=[Depends(perm_election)],
)
async def create_nominee(db_session: database.DBSession, body: Nominee):
    await nominees.crud.create_nominee_info(
        db_session,
        NomineeInfoDB(
            computing_id=body.computing_id,
            full_name=body.full_name,
            linked_in=body.linked_in,
            instagram=body.instagram,
            email=body.email,
            discord_username=body.discord_username,
        ),
    )

    nominee_info = await nominees.crud.get_nominee_info(db_session, body.computing_id)
    if nominee_info is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="couldn't fetch newly created nominee"
        )

    return JSONResponse(nominee_info)


@router.get(
    "/{computing_id}",
    description="Nominee info is always publically tied to election, so be careful!",
    response_model=Nominee,
    responses={404: {"description": "nominee doesn't exist"}},
    operation_id="get_nominee",
    dependencies=[Depends(perm_election)],
)
async def get_nominee_info(db_session: database.DBSession, computing_id: str):
    # Putting this one behind the admin wall since it has contact information
    nominee_info = await nominees.crud.get_nominee_info(db_session, computing_id)
    if nominee_info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="nominee doesn't exist")

    return JSONResponse(nominee_info.serialize())


@router.delete(
    "/{computing_id}",
    description="Delete a nominee",
    operation_id="delete_nominee",
    dependencies=[Depends(perm_election)],
)
async def delete_nominee_info(db_session: database.DBSession, computing_id: str):
    await nominees.crud.delete_nominee_info(db_session, computing_id)
    await db_session.commit()


@router.patch(
    "/{computing_id}",
    description="Updates an exisint nominee. Returns an updated copy of their nominee info.",
    response_model=Nominee,
    responses={
        404: {"description": "Nominee doesn't exist."},
        500: {"description": "Failed to retrieve updated nominee."},
    },
    operation_id="update_nominee",
    dependencies=[Depends(perm_election)],
)
async def provide_nominee_info(db_session: database.DBSession, body: NomineeUpdate, computing_id: str):
    nominee_entry = await nominees.crud.get_nominee_info(db_session, computing_id)
    updated_data = body.model_dump(exclude_unset=True)
    for k, v in updated_data.items():
        setattr(nominee_entry, k, v)
    await db_session.commit()
    await db_session.refresh(nominee_entry)

    return JSONResponse(Nominee.model_validate(nominee_entry).model_dump(mode="json", exclude_unset=True))
