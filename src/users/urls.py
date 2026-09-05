from fastapi import APIRouter, Depends

import database
import users.crud
from auth.models import SiteUser
from dependencies import perm_admin
from utils.shared_models import DetailModel

router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[Depends(perm_admin)],
)


@router.get(
    "",
    description="Get all nominees",
    response_model=list[SiteUser],
    responses={403: {"description": "need to be an admin", "model": DetailModel}},
    operation_id="get_all_nominees",
)
async def get_all_users(
    db_session: database.DBSession,
):
    nominees_list = await users.crud.get_all_users(db_session)

    return [SiteUser.model_validate(user) for user in nominees_list]
