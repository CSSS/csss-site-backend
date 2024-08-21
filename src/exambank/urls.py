import os
from typing import Optional

import auth.crud
import database
import exambank.crud
from exambank.watermark import apply_watermark, create_watermark, raster_pdf
from fastapi import APIRouter, HTTPException, JSONResponse, Request, Response
from permission.types import ExamBankAccess
from utils import path_in_dir

EXAM_BANK_DIR = "/opt/csss-site/media/exam-bank"

router = APIRouter(
    prefix="/exam-bank",
    tags=["exam-bank"],
)

# TODO: update endpoints to use crud functions

@router.get(
    "/list/exams"
)
async def all_exams(
    request: Request,
    db_session: database.DBSession,
    course_id_starts_with: str | None,
):
    courses = [f.name for f in os.scandir(f"{EXAM_BANK_DIR}") if f.is_dir()]
    if course_id_starts_with is not None:
        courses = [course for course in courses if course.startswith(course_id_starts_with)]

    exam_list = exambank.crud.all_exams(db_session, course_id_starts_with)
    return JSONResponse([exam.serializable_dict() for exam in exam_list])

@router.get(
    "/list/courses"
)
async def all_courses(
    _request: Request,
    _db_session: database.DBSession,
):
    # TODO: replace this with a table eventually
    courses = [f.name for f in os.scandir(f"{EXAM_BANK_DIR}") if f.is_dir()]
    return JSONResponse(courses)

@router.get(
    "/get/{exam_id}"
)
async def get_exam(
    request: Request,
    db_session: database.DBSession,
    exam_id: int,
):
    session_id = request.cookies.get("session_id", None)
    if session_id is None:
        raise HTTPException(status_code=401)

    computing_id = await auth.crud.get_computing_id(db_session, session_id)
    if computing_id is None:
        raise HTTPException(status_code=401)

    # TODO: clean this checking into one function & one computing_id check
    if not await ExamBankAccess.has_permission(request):
        raise HTTPException(status_code=401, detail="user must have exam bank access permission")

    # number exams with an exam_id pkey
    # TODO: store resource locations in a db table & simply look them up

    meta = exambank.crud.exam_metadata(db_session, exam_id)
    if meta is None:
        raise HTTPException(status_code=400, detail=f"could not find the exam with exam_id={exam_id}")

    exam_path = f"{EXAM_BANK_DIR}/{meta.pdf_path}"
    if not path_in_dir(exam_path, EXAM_BANK_DIR):
        raise HTTPException(status_code=500, detail="Found dangerous pdf path, exiting")

    # TODO: test this works nicely
    watermark = create_watermark(computing_id, 20)
    watermarked_pdf = apply_watermark(exam_path, watermark)
    image_bytes = raster_pdf(watermarked_pdf)

    headers = { "Content-Disposition": f'inline; filename="{meta.course_id}_{exam_id}_{computing_id}.pdf"' }
    return Response(content=image_bytes, headers=headers, media_type="application/pdf")

