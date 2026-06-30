from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

import database
import honorary.crud
from dependencies import perm_admin
from honorary.models import HonoraryMember, HonoraryMemberCreate, HonoraryMemberUpdate
from honorary.tables import HonoraryMemberDB
from utils.shared_models import DetailModel, SuccessResponse

router = APIRouter(
    prefix="/honorary",
    tags=["honorary"],
)


@router.get(
    "",
    description="Get all honorary member terms",
    response_model=list[HonoraryMember],
    responses={403: {"description": "must be a website admin", "model": DetailModel}},
    operation_id="get_all_honorary_members",
    dependencies=[Depends(perm_admin)],
)
async def get_all_honorary_members(db_session: database.DBSession):
    honorary_members = await honorary.crud.get_all_honorary_members(db_session)
    return JSONResponse(
        [
            HonoraryMember.model_validate(member).model_dump(mode="json", exclude_unset=True)
            for member in honorary_members
        ]
    )


@router.get(
    "/current",
    description="Get all active honorary member terms",
    response_model=list[HonoraryMember],
    responses={403: {"description": "must be a website admin", "model": DetailModel}},
    operation_id="get_current_honorary_members",
    dependencies=[Depends(perm_admin)],
)
async def get_current_honorary_members(db_session: database.DBSession):
    honorary_members = await honorary.crud.get_current_honorary_members(db_session)
    return JSONResponse(
        [
            HonoraryMember.model_validate(member).model_dump(mode="json", exclude_unset=True)
            for member in honorary_members
        ]
    )


@router.post(
    "",
    description="Create honorary member terms",
    response_model=list[HonoraryMember],
    responses={
        403: {"description": "must be a website admin", "model": DetailModel},
        500: {"description": "failed to create honorary member terms", "model": DetailModel},
    },
    operation_id="create_honorary_members",
    dependencies=[Depends(perm_admin)],
)
async def create_honorary_members(
    db_session: database.DBSession,
    body: list[HonoraryMemberCreate],
):
    new_members = [HonoraryMemberDB(**member.model_dump()) for member in body]
    created_members = await honorary.crud.create_honorary_members(db_session, new_members)

    await db_session.flush()

    content = [
        HonoraryMember.model_validate(member).model_dump(mode="json", exclude_unset=True) for member in created_members
    ]

    await db_session.commit()

    return JSONResponse(content)


@router.patch(
    "/{term_id}",
    description="Update an honorary member term. Ended terms cannot be updated.",
    response_model=HonoraryMember,
    responses={
        403: {"description": "must be a website admin", "model": DetailModel},
        404: {"description": "honorary member term does not exist", "model": DetailModel},
        409: {"description": "honorary member term has already ended", "model": DetailModel},
    },
    operation_id="update_honorary_member",
    dependencies=[Depends(perm_admin)],
)
async def update_honorary_member(
    db_session: database.DBSession,
    term_id: int,
    body: HonoraryMemberUpdate,
):
    honorary_member = await honorary.crud.get_honorary_member_by_id(db_session, term_id)
    if honorary_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"honorary member term with id={term_id} does not exist",
        )

    if honorary.crud.has_term_ended(honorary_member):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot update a term that has already ended",
        )

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(honorary_member, key, value)

    await db_session.commit()
    await db_session.refresh(honorary_member)

    return JSONResponse(HonoraryMember.model_validate(honorary_member).model_dump(mode="json", exclude_unset=True))


@router.delete(
    "/{term_id}",
    description="Delete an honorary member term. Ended terms cannot be deleted.",
    response_model=SuccessResponse,
    responses={
        403: {"description": "must be a website admin", "model": DetailModel},
        404: {"description": "honorary member term does not exist", "model": DetailModel},
        409: {"description": "honorary member term has already ended", "model": DetailModel},
    },
    operation_id="delete_honorary_member",
    dependencies=[Depends(perm_admin)],
)
async def delete_honorary_member(
    db_session: database.DBSession,
    term_id: int,
):
    honorary_member = await honorary.crud.get_honorary_member_by_id(db_session, term_id)
    if honorary_member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"honorary member term with id={term_id} does not exist",
        )

    if honorary.crud.has_term_ended(honorary_member):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="cannot delete a term that has already ended",
        )

    await honorary.crud.delete_honorary_member(db_session, honorary_member)
    await db_session.commit()

    return SuccessResponse(success=True)
