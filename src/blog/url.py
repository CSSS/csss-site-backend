import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import auth
import blog.crud
import database

_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/blog",
    tags=["blog"],
)
