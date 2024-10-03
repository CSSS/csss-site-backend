import auth.crud
import database
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from permission.types import WebsiteAdmin

router = APIRouter(
    prefix="/permission",
    tags=["permission"],
)

@router.get(
    "/is_admin",
    description="checks if the current user has the admin permission"
)
async def is_admin(
    request: Request,
    db_session: database.DBSession,
):
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401, detail="must be logged in")

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if computing_id is None:
        raise HTTPException(status_code=401, detail="must be logged in (no computing_id)")

    is_admin_permission = await WebsiteAdmin.has_permission(db_session, computing_id)
    return JSONResponse({"is_admin": is_admin_permission})
