from fastapi import APIRouter, HTTPException, Request

import database

from permission.types import ExamBankAccess
from exambank.watermark import raster_pdf_from_path

EXAM_BANK_DIR = "/opt/csss-site/media/exam-bank"

router = APIRouter(
    prefix="/exam-bank",
    tags=["exam-bank"],
)

@router.get(
    "/list"
)
async def all_exams(
    request: Request,
    db_session: database.DBSession,
    course_name_starts_with: str,
    exam_title_starts_with: str,
):
    # TODO: implement this
    pass

@router.get(
    "/"
)
async def get_exam(
    request: Request,
    db_session: database.DBSession, 
    course_name: str,
    exam_title: str,
):
    if not await ExamBankAccess.has_permission(request):
        raise HTTPException(status_code=401, detail="user must have exam bank access permission")
  
    # TODO: implement this too

    # TODO: get list of files in dir & find the one we're looking for
    #if title in EXAM_BANK_DIR:

    #raster_pdf_from_path()

