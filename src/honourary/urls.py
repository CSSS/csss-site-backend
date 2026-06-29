from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

import database
import honourary.crud
from dependencies import perm_admin
from honourary.models import HonoraryMember, HonoraryMemberCreate, HonoraryMemberUpdate
from honourary.tables import HonoraryMemberDB
from utils.shared_models import SuccessResponse

router = APIRouter(
    prefix="/honourary",
    tags=["honourary"],
)


@router.get(
    "",
    description="Get all honourary member terms",
    response_model=list[HonoraryMember],
    operation_id="get_all_honourary_members",
    dependencies=[Depends(perm_admin)],
)
async def get_all_honourary_members(db_session: database.DBSession):
    honorary_members = await honourary.crud.get_all_honorary_members(db_session)
    return JSONResponse(
        [
            HonoraryMember.model_validate(member).model_dump(mode="json", exclude_unset=True)
            for member in honorary_members
        ]
    )


@router.get(
    "/current",
    description="Get all active honourary member terms",
    response_model=list[HonoraryMember],
    operation_id="get_current_honourary_members",
    dependencies=[Depends(perm_admin)],
)
async def get_current_honourary_members(db_session: database.DBSession):
    honorary_members = await honourary.crud.get_current_honorary_members(db_session)
    return JSONResponse(
        [
            HonoraryMember.model_validate(member).model_dump(mode="json", exclude_unset=True)
            for member in honorary_members
        ]
    )


@router.post(
    "",
    description="Create honourary member terms",
    response_model=list[HonoraryMember],
    operation_id="create_honourary_members",
    dependencies=[Depends(perm_admin)],
)
async def create_honourary_members(
    db_session: database.DBSession,
    body: list[HonoraryMemberCreate],
):
    new_members = [HonoraryMemberDB(**member.model_dump()) for member in body]
    created_members = await honourary.crud.create_honorary_members(db_session, new_members)

    await db_session.commit()

    return JSONResponse(
        [
            HonoraryMember.model_validate(member).model_dump(mode="json", exclude_unset=True)
            for member in created_members
        ]
    )


@router.patch(
    "/{term_id}",
    description="Update an honourary member term. Ended terms cannot be updated.",
    response_model=HonoraryMember,
    operation_id="update_honourary_member",
    dependencies=[Depends(perm_admin)],
)
async def update_honourary_member(
    db_session: database.DBSession,
    term_id: int,
    body: HonoraryMemberUpdate,
):
    honorary_member = await honourary.crud.get_honorary_member_by_id_or_raise(db_session, term_id)
    honourary.crud.ensure_term_has_not_ended(honorary_member)

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(honorary_member, key, value)

    await db_session.commit()
    await db_session.refresh(honorary_member)

    return JSONResponse(HonoraryMember.model_validate(honorary_member).model_dump(mode="json", exclude_unset=True))


@router.delete(
    "/{term_id}",
    description="Delete an honourary member term. Ended terms cannot be deleted.",
    response_model=SuccessResponse,
    operation_id="delete_honourary_member",
    dependencies=[Depends(perm_admin)],
)
async def delete_honourary_member(
    db_session: database.DBSession,
    term_id: int,
):
    honorary_member = await honourary.crud.get_honorary_member_by_id_or_raise(db_session, term_id)
    honourary.crud.ensure_term_has_not_ended(honorary_member)

    await honourary.crud.delete_honorary_member(db_session, honorary_member)
    await db_session.commit()

    return SuccessResponse(success=True)
