from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

import database
import users.crud
from auth.models import SiteUser
from auth.tables import SiteUserDB, SiteUserRoleDB
from constants import TZ_INFO
from dependencies import SiteAdmin, perm_admin
from users.models import SiteUserCreate
from utils.shared_models import DetailModel

router = APIRouter(
    prefix="/user",
    tags=["user"],
)


@router.get(
    "",
    description="Get all site users.",
    response_model=list[SiteUser],
    responses={403: {"description": "need to be an admin", "model": DetailModel}},
    operation_id="get_all_users",
    dependencies=[Depends(perm_admin)],
)
async def get_all_users(
    db_session: database.DBSession,
):
    users_list = await users.crud.get_all_users(db_session)

    try:
        response = [SiteUser.model_validate(user) for user in users_list]
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="validation error from database"
        ) from e

    return response


@router.post(
    "",
    description="Create a site user.",
    response_model=SiteUser,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "need to be a logged in admin", "model": DetailModel},
        403: {"description": "need to be an admin", "model": DetailModel},
        409: {"description": "user already existed", "model": DetailModel},
    },
    operation_id="create_site_user",
)
async def create_site_user(db_session: database.DBSession, admin_id: SiteAdmin, body: SiteUserCreate):
    user_db = SiteUserDB(computing_id=body.computing_id)

    users.crud.create_site_user(db_session, user_db)

    if body.roles:
        now = datetime.now(tz=TZ_INFO)
        user_roles = [
            SiteUserRoleDB(
                computing_id=body.computing_id,
                role=role,
                added_by=admin_id,
                created_at=now,
            )
            for role in body.roles
        ]
        users.crud.create_user_roles(db_session, user_roles)

    try:
        await db_session.flush()
        await db_session.refresh(
            user_db,
            attribute_names=[
                "computing_id",
                "first_logged_in",
                "last_logged_in",
                "roles",
            ],
        )
        new_user = SiteUser.model_validate(user_db)
        await db_session.commit()
    except IntegrityError:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Site user already exists",
        ) from None

    return new_user
