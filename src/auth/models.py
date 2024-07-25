from datetime import datetime

from constants import COMPUTING_ID_LEN, SESSION_ID_LEN
from database import Base
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship


class UserSession(Base):
    __tablename__ = "user_session"

    # note: a primary key is required for every database table
    computing_id = Column(
        String(COMPUTING_ID_LEN), nullable=False, primary_key=True
    )

    # time the CAS ticket was issued
    issue_time = Column(DateTime, nullable=False)

    session_id = Column(
        String(SESSION_ID_LEN), nullable=False, unique=True
    )  # the space needed to store 256 bytes in base64


class SiteUser(Base):
    # user is a reserved word in postgres
    # see: https://stackoverflow.com/questions/22256124/cannot-create-a-database-table-named-user-in-postgresql
    __tablename__ = "site_user"

    # note: a primary key is required for every database table
    computing_id = Column(
        String(COMPUTING_ID_LEN),
        #ForeignKey("user_session.computing_id"),
        nullable=False,
        primary_key=True,
    )

    # first and last time logged into the CSSS API
    # note: default date (for pre-existing columns) is June 16th, 2024
    first_logged_in = Column(DateTime, nullable=False, default=datetime(2024, 6, 16))
    last_logged_in = Column(DateTime, nullable=False, default=datetime(2024, 6, 16))
