from dataclasses import dataclass

import database


@dataclass
class ExamMetadata:
    exam_id: int
    pdf_path: str
    course_id: str

async def create_exam():
    # for admins to run manually
    # TODO: implement this later; for now just upload data manually
    pass

async def update_exam():
    # for admins to run manually
    # TODO: implement this later; for now just upload data manually
    pass

async def all_exams(
    db_session: database.DBSession,
    course_starts_with: None | str,
):
    # go through all exams (sorted by exam_id) & filter those which start with course_starts_with
    # .like(f"%{course_starts_with}")
    pass

async def exam_metadata(
    db_session: database.DBSession,
    exam_id: int,
) -> ExamMetadata:
    # TODO: implement this function
    pass

async def update_description():
    # TODO: implement this eventually, if we want students to contribute to
    # the exam description
    pass

