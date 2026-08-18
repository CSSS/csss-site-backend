from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from constants import AUTH_REDIRECT_ID_LEN, COMPUTING_ID_LEN, SESSION_ID_LEN
from database import Base


class UserSessionDB(Base):
    __tablename__ = "user_session"

    session_id: Mapped[str] = mapped_column(
        String(SESSION_ID_LEN),
        nullable=False,
        primary_key=True,
    )

    computing_id: Mapped[str] = mapped_column(
        String(COMPUTING_ID_LEN), ForeignKey("site_user.computing_id"), index=True, nullable=False
    )

    # TODO: Make all timestamps uneditable later
    # time the CAS ticket was issued
    issue_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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


class AuthRedirectDB(Base):
    __tablename__ = "auth_redirect"

    id: Mapped[str] = mapped_column(String(AUTH_REDIRECT_ID_LEN), primary_key=True)
    return_to: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[str] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
