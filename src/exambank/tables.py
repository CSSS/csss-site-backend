from datetime import datetime

from constants import COMPUTING_ID_LEN, SESSION_ID_LEN, SESSION_TYPE_LEN
from database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

# TODO: determine what info will need to be in the spreadsheet, then moved here

# TODO: move this to types.py
class ExamKind:
    FINAL = "final"
    MIDTERM = "midterm"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    NOTES = "notes"
    MISC = "misc"

class ExamMetadata(Base):
    __tablename__ = "exam_metadata"

    exam_id = Column(Integer, primary_key=True, autoincrement=True)
    upload_date = Column(DateTime, nullable=False)
    # with EXAM_BANK_DIR as the root
    pdf_path = Column(String(128), nullable=False)

    # formatted f"{faculty} {course_number}"
    course_id = Column(String(16), nullable=True)
    primary_author = Column(Integer, nullable=False) # foreign key constraint
    title = Column(String(64), nullable=True) # Something like "Midterm 2" or "Computational Geometry Final"
    # TODO: if this gets big, maybe separate it to a different table
    description = Column(Text, nullable=True) # For a natural language description of the contents
    kind = Column(String(16), nullable=False)

    # TODO: on the resulting output table, include xxxx-xx-xx for unknown dates
    year = Column(Integer, nullable=True)
    month = Column(Integer, nullable=True)
    day = Column(Integer, nullable=True)

class Professor(Base):
    __tablename__ = "professor"

    professor_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False)
    info_url = Column(String(128), nullable=False)

    computing_id = Column(
        String(COMPUTING_ID_LEN),
        # Foreign key constriant w/ users table
        #ForeignKey("user_session.computing_id"),
        nullable=True,
    )

# TODO: eventually implement a table for courses & course info; hook it in with the rest of the site & coursys api

