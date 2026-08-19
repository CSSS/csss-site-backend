from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from auth.constants import SITE_USER_ROLE_MAX_LENGTH, UserRole
from constants import AUTH_REDIRECT_ID_LEN, COMPUTING_ID_LEN, SESSION_ID_LEN
from database import Base


class UserSessionDB(Base):
    __tablename__ = "user_session"

    session_hash: Mapped[str] = mapped_column(
        LargeBinary(32),
        primary_key=True,
    )

    computing_id: Mapped[str] = mapped_column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id"),
        index=True,
    )

    # TODO: Make all timestamps uneditable later
    # time the CAS ticket was issued
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


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


class SiteUserRoleDB(Base):
    """
    Defines what role a user has.

    Attributes:
        __tablename__: site_user_role
        computing_id: computing ID of the user, references site_user
        role: the role of the user on the site
        added_by: the computing ID of the site user who added this user, references site_user
        created_at: the datetimetz of when this role was added
    """

    __tablename__ = "site_user_role"

    computing_id: Mapped[str] = mapped_column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id"),
        primary_key=True,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [role.value for role in enum],
            name="role_valid",
        ),
        primary_key=True,
        index=True,
    )

    added_by: Mapped[str | None] = mapped_column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class AuthRedirectDB(Base):
    """
    Keeps track of the return URL for a user while they log in via CAS.

    Attributes:
        __tablename__: auth_redirect
        id: their login attempt identifier
        return_to: their redirect URL
        expires_at: the datetime when the login attempt expires
        created_at: the datetime when the login attempt was created
    """

    __tablename__ = "auth_redirect"

    id: Mapped[str] = mapped_column(String(AUTH_REDIRECT_ID_LEN), primary_key=True)
    return_to: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
