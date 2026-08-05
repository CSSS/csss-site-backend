from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from constants import COMPUTING_ID_LEN, SESSION_ID_LEN
from database import Base


class UserSessionDB(Base):
    __tablename__ = "user_session"

    computing_id: Mapped[str] = mapped_column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id"),
        # in psql pkey means non-null
        primary_key=True,
    )

    # TODO: Make all timestamps uneditable later
    # time the CAS ticket was issued
    issue_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    session_id: Mapped[str] = mapped_column(
        String(SESSION_ID_LEN), nullable=False, unique=True
    )  # the space needed to store 32 bytes in base64


class SiteUserDB(Base):
    # user is a reserved word in postgres
    # see: https://stackoverflow.com/questions/22256124/cannot-create-a-database-table-named-user-in-postgresql
    __tablename__ = "site_user"

    computing_id: Mapped[str] = mapped_column(
        String(COMPUTING_ID_LEN),
        primary_key=True,
    )

    # first and last time logged into the CSSS API
    first_logged_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_logged_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
