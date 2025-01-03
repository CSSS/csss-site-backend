import os

import sqlalchemy
from fastapi import APIRouter, HTTPException, JSONResponse, Request, Response
from tables import Course, ExamMetadata, Professor

import database
import exambank.crud
from auth.utils import logged_in_or_raise
from exambank.watermark import apply_watermark, create_watermark, raster_pdf
from permission.types import ExamBankAccess
from utils import path_in_dir

# all exams are stored here, and for the time being must be manually moved here
EXAM_BANK_DIR = "/opt/csss-site/media/exam-bank"

router = APIRouter(
    prefix="/exam-bank",
    tags=["exam-bank"],
)

# TODO: update endpoints to use crud functions -> don't use crud actually; refactor to do that later

@router.get(
    "/metadata"
)
async def exam_metadata(
    request: Request,
    db_session: database.DBSession,
):
    _, _ = await logged_in_or_raise(request, db_session)
    await ExamBankAccess.has_permission_or_raise(request, errmsg="user must have exam bank access permission")

    """
    courses = [f.name for f in os.scandir(f"{EXAM_BANK_DIR}") if f.is_dir()]
    if course_id_starts_with is not None:
        courses = [course for course in courses if course.startswith(course_id_starts_with)]

    exam_list = exambank.crud.all_exams(db_session, course_id_starts_with)
    return JSONResponse([exam.serializable_dict() for exam in exam_list])
    """

    # TODO: test that the joins work correctly
    exams = await db_session.scalar(
        sqlalchemy
        .select(ExamMetadata, Professor, Course)
        .join(Professor)
        .join(Course, isouter=True) # we want to have null values if the course is not known
        .order_by(Course.course_number)
    )

    print(exams)

    # TODO: serialize exams somehow
    return JSONResponse(exams)

# TODO: implement endpoint to fetch exams
"""
@router.get(
    "/exam/{exam_id}"
)
async def get_exam(
    request: Request,
    db_session: database.DBSession,
    exam_id: int,
):
    _, session_computing_id = await logged_in_or_raise(request, db_session)
    await ExamBankAccess.has_permission_or_raise(request, errmsg="user must have exam bank access permission")

    # number exams with an exam_id pkey
    # TODO: store resource locations in a db table & simply look them up

    meta = exambank.crud.exam_metadata(db_session, exam_id)
    if meta is None:
        raise HTTPException(status_code=400, detail=f"could not find the exam with exam_id={exam_id}")

    exam_path = f"{EXAM_BANK_DIR}/{meta.pdf_path}"
    if not path_in_dir(exam_path, EXAM_BANK_DIR):
        raise HTTPException(status_code=500, detail="Found dangerous pdf path, exiting")

    # TODO: test this works nicely
    watermark = create_watermark(session_computing_id, 20)
    watermarked_pdf = apply_watermark(exam_path, watermark)
    image_bytes = raster_pdf(watermarked_pdf)

    headers = { "Content-Disposition": f'inline; filename="{meta.course_id}_{exam_id}_{session_computing_id}.pdf"' }
    return Response(content=image_bytes, headers=headers, media_type="application/pdf")
"""
