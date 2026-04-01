import logging

from fastapi import APIRouter, Request, HTTPException, status
import fastapi.responses import JSONResponse

import auth
import announcements.crud   
import database
from permission.types import OfficerPrivateInfo

_logger = logging.getLogger(__name__)

router =  APIRouter(
    prefix="/announcements",
    tags=["announcements"],
)

@router.get("",
            response_class=JSONResponse,
    status_code=status.HTTP_200_OK,
)
async def get_announcements(request: Request):
    return {"message": "This is the announcements endpoint."}