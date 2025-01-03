from datetime import datetime
from types import ExamKind

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from constants import COMPUTING_ID_LEN, SESSION_ID_LEN, SESSION_TYPE_LEN
from database import Base

# TODO: determine what info will need to be in the spreadsheet, then moved here

class ExamMetadata(Base):
    __tablename__ = "exam_metadata"

    # exam_id is the number used to access the exam
    exam_id = Column(Integer, primary_key=True)
    upload_date = Column(DateTime, nullable=False)
    exam_pdf_size = Column(Integer, nullable=False) # in bytes

    author_id = Column(String(COMPUTING_ID_LEN), ForeignKey("professor.professor_id"), nullable=False)
    # whether this is the confirmed author of the exam, or just suspected
    author_confirmed = Column(Boolean, nullable=False)
    # true if the professor has given permission for us to use their exam
    author_permission = Column(Boolean, nullable=False)

    kind = Column(String(24), nullable=False)
    course_id = Column(String(COMPUTING_ID_LEN), ForeignKey("course.professor_id"), nullable=True)
    title = Column(String(96), nullable=True) # Something like "Midterm 2" or "Computational Geometry Final"
    description = Column(Text, nullable=True) # For a natural language description of the contents

    # formatted as xxxx-xx-xx, include x for unknown dates
    date_string = Column(String(10), nullable=False)

# TODO: eventually hook the following tables in with the rest of the site & coursys api

class Professor(Base):
    __tablename__ = "professor"

    professor_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    info_url = Column(String(128), nullable=False) # A url which provides more information about the professor

    # we may not know a professor's computing_id
    computing_id = Column(String(COMPUTING_ID_LEN), ForeignKey("user_session.computing_id"), nullable=True)

class Course(Base):
    __tablename__ = "course"

    course_id = Column(Integer, primary_key=True, autoincrement=True)

    # formatted f"{faculty} {course_number}", ie. CMPT 300
    course_faculty = Column(String(12), nullable=False)
    course_number = Column(String(12), nullable=False)
    course_name = Column(String(96), nullable=False)

