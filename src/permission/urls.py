from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from dependencies import perm_admin

router = APIRouter(
    prefix="/permission",
    tags=["permission"],
)


@router.get(
    "/is_admin",
    description="checks if the current user has the admin permission",
    dependencies=[Depends(perm_admin)],
)
async def is_admin():
    # session_id = request.cookies.get("session_id", None)
    # if session_id is None:
    #     raise HTTPException(status_code=401, detail="must be logged in")
    #
    # computing_id = await auth.crud.get_computing_id(db_session, session_id)
    # if computing_id is None:
    #     raise HTTPException(status_code=401, detail="must be logged in (no computing_id)")
    #
    # is_admin_permission = await WebsiteAdmin.has_permission(db_session, computing_id)
    return JSONResponse({"is_admin": True})
