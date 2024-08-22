import logging

import auth
import blog.crud
import database
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from permission.types import OfficerPrivateInfo

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/blog_entries",
    tags=["blog_entries"],
)
