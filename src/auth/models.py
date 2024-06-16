from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import mapped_column
# from sqlalchemy.orm import relationship

from database import Base


class UserSession(Base):
    __tablename__ = "user_session"

    # primary key for a given user session
    id = Column(Integer, primary_key=True)

    # time the CAS ticket was issued
    issue_time = Column(DateTime, nullable=False)

    # session ID given to a browser to store in cookies
    # 512 bytes: the space needed to store 256 bytes in base64
    session_id = Column(String(512), nullable=False)

    # SFU computing ID of the user
    computing_id = Column(
        String(32), nullable=False
    )  # used to refer to a row in the site_user table


class User(Base):
    # user is a reserved word in postgres
    # see: https://stackoverflow.com/questions/22256124/cannot-create-a-database-table-named-user-in-postgresql
    __tablename__ = "site_user"

    # note: a primary key is required for every database table
    id = Column(Integer, primary_key=True)

    # SFU computing ID of the user
    computing_id = Column(
        String(32), nullable=False
    )  # technically a max of 8 digits https://www.sfu.ca/computing/about/support/tips/sfu-userid.html

    # first and last time logged into the CSSS API
    # note: default date (for pre-existing columns) is June 16th, 2024
    first_logged_in = Column(DateTime, nullable=False, default=datetime(2024, 6, 16))
    last_logged_in = Column(DateTime, nullable=False, default=datetime(2024, 6, 16))
