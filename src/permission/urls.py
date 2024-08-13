
import auth.crud
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from permission.types import WebsiteAdmin

router = APIRouter(
    prefix="/permission",
    tags=["permission"],
)

# TODO: add an endpoint for viewing permissions that exist & what levels they can have & what levels each person has
@router.get(
    "/is_admin",
    description="checks if the current user has the admin permission"
)
def is_admin(
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        return JSONResponse({"is_admin": False})
    
    # what if user doesn't have a computing id?
    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    is_admin_permission = await WebsiteAdmin.has_permission(db_session, computing_id)
    return JSONResponse({"is_admin": is_admin_permission})
