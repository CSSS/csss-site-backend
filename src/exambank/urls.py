import os
from typing import Optional

import auth.crud
import database
from exambank.watermark import apply_watermark, create_watermark, raster_pdf
from fastapi import APIRouter, HTTPException, JSONResponse, Request, Response
from permission.types import ExamBankAccess

EXAM_BANK_DIR = "/opt/csss-site/media/exam-bank"

router = APIRouter(
    prefix="/exam-bank",
    tags=["exam-bank"],
)

@router.get(
    "/list/exams"
)
async def all_exams(
    request: Request,
    db_session: database.DBSession,
    course_name_starts_with: str | None,
    exam_title_starts_with: str | None,
):
    courses = [f.name for f in os.scandir(f"{EXAM_BANK_DIR}") if f.is_dir()]
    if course_name_starts_with is not None:
        courses = [course for course in courses if course.startswith(course_name_starts_with)]

    exams = []
    for course in courses:
        exams += [
            f.name for f in os.scandir(f"{EXAM_BANK_DIR}/{course}")
            if f.is_file() and f.name.endswith(".pdf") and (
                exam_title_starts_with is None
                or f.name.startswith(exam_title_starts_with)
            )
        ]

    return JSONResponse(exams)

@router.get(
    "/list/courses"
)
async def all_courses(
    _request: Request,
    _db_session: database.DBSession,
    course_name_starts_with: str | None,
):
    courses = [f.name for f in os.scandir(f"{EXAM_BANK_DIR}") if f.is_dir()]
    if course_name_starts_with is not None:
        courses = [
            course for course in courses
            if course.startswith(course_name_starts_with)
        ]

    return JSONResponse(courses)

@router.get(
    "/"
)
async def get_exam(
    request: Request,
    db_session: database.DBSession,
    course_name: str,
    exam_title: str,
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

    course_folders = [f.name for f in os.scandir(EXAM_BANK_DIR) if f.is_dir()]
    if course_name in course_folders:
        exams = [
            f.name[:-4]
            for f in os.scandir(f"{EXAM_BANK_DIR}/{course_name}")
            if f.is_file() and f.name.endswith(".pdf")
        ]
        if exam_title in exams:
            # TODO: test this works nicely
            exam_path = f"{EXAM_BANK_DIR}/{course_name}/{exam_title}.pdf"
            watermark = create_watermark(computing_id, 20)
            watermarked_pdf = apply_watermark(exam_path, watermark)
            image_bytes = raster_pdf(watermarked_pdf)

            headers = { "Content-Disposition": f'inline; filename="{exam_title}_{computing_id}.pdf"' }
            return Response(content=image_bytes, headers=headers, media_type="application/pdf")

    raise HTTPException(status_code=400, detail="could not find the requested exam")

