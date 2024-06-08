from constants import COMPUTING_ID_LEN, SESSION_ID_LEN
from database import Base
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship


class UserSession(Base):
    __tablename__ = "user_session"

    # note: a primary key is required for every database table
    computing_id = Column(
        String(COMPUTING_ID_LEN), nullable=False, primary_key=True, unique=True
    )  # technically a max of 8 digits https://www.sfu.ca/computing/about/support/tips/sfu-userid.html

    issue_time = Column(DateTime, nullable=False)
    session_id = Column(
        String(SESSION_ID_LEN), nullable=False, unique=True
    )  # the space needed to store 256 bytes in base64

    site_user = relationship("User")


class User(Base):
    # user is a reserved word in postgres
    # see: https://stackoverflow.com/questions/22256124/cannot-create-a-database-table-named-user-in-postgresql
    __tablename__ = "site_user"

    # note: a primary key is required for every database table
    computing_id = Column(
        String(COMPUTING_ID_LEN),
        ForeignKey("user_session.computing_id"),
        nullable=False,
        primary_key=True,
        unique=True,
    )  # technically a max of 8 digits https://www.sfu.ca/computing/about/support/tips/sfu-userid.html

    officer_term = relationship("OfficerTerm")
    officer_info = relationship("OfficerInfo")

    # TODO: (#13) add two new columns for storing the initial date & last date logged in.
    # When running the migration, you'll want to decide on some random date to be the default for users who've logged
    # before but haven't
