from __future__ import annotations

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import BigInteger, Date, Enum, Integer, String, Text

from constants import (
    COMPUTING_ID_LEN,
    DISCORD_ID_LEN,
    DISCORD_NAME_LEN,
    DISCORD_NICKNAME_LEN,
    GITHUB_USERNAME_LEN,
    GMAIL_MAX_LEN,
    PHONE_NUMBER_MAX_LEN,
)
from database import Base
from officers.constants import (
    OFFICER_NAME_MAX_LEN,
    OFFICER_POSITION_CATEGORY_MAX_LEN,
    OFFICER_POSITION_MAX_LEN,
    TERM_DATA_COURSE_MAX_LEN,
    TERM_DATA_PL_MAX_LEN,
    OfficerPositionTypeEnum,
)


class OfficerInfoDB(Base):
    """

    Attributes:
        __tablename__: officer_info
        id: unique ID
        computing_id: SFU Computing ID
        legal_name: legal name
        preferred_name: preferred first name
        phone_number: phone number
        discord_id: Discord Snowflake ID
        google_drive_email: what they use to access Gmail, include the email domain e.g. example@gmail.com
        github_username: GitHub username
    """

    __tablename__ = "officer_info"

    __table_args__ = (
        CheckConstraint(
            "computing_id IS NULL OR (computing_id ~ '^[a-z0-9]+$' AND computing_id = lower(computing_id))",
            name="computing_id_format",
        ),
        CheckConstraint("legal_name IS NOT NULL AND btrim(legal_name) <> ''", name="legal_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    computing_id: Mapped[str | None] = mapped_column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    legal_name: Mapped[str] = mapped_column(
        String(OFFICER_NAME_MAX_LEN),
    )

    preferred_name: Mapped[str | None] = mapped_column(
        String(OFFICER_NAME_MAX_LEN),
        nullable=True,
    )

    phone_number: Mapped[str | None] = mapped_column(
        String(PHONE_NUMBER_MAX_LEN),
        nullable=True,
    )

    discord_id: Mapped[str | None] = mapped_column(
        String(DISCORD_ID_LEN),
        nullable=True,
        unique=True,
    )

    google_drive_email: Mapped[str | None] = mapped_column(
        String(GMAIL_MAX_LEN),
        nullable=True,
    )

    github_username: Mapped[str | None] = mapped_column(
        String(GITHUB_USERNAME_LEN),
        nullable=True,
    )

    terms: Mapped[list[OfficerTermDB]] = relationship(
        back_populates="officer",
    )


class OfficerPositionDB(Base):
    """
    The canonical list of every single Officer position.

    Attributes:
        __tablename__: officer_position
        id: unique ID
        position: the name of the position
    """

    __tablename__ = "officer_position"

    __table_args__ = (
        CheckConstraint("position IS NOT NULL AND btrim(position) <> ''", name="position_not_blank"),
        Index("lower_case", text("lower(btrim(position))"), unique=True),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    position: Mapped[str] = mapped_column(
        String(OFFICER_POSITION_MAX_LEN),
        nullable=False,
    )


class OfficerPositionVersionDB(Base):
    """
    The version of an officer position and how long they were used for.

    Attributes:
        __tablename__: officer_position_version
        id: unique ID
        position_id: officer_position.id of this version
        position: use `joinedload()` to get the string representation of the position
        category: the type of officer (executive, appointed representative, or elected representative)
        multiple_allowed: true if multiple people can hold this executive position simulteneously, false if not, NULL/None if the position is not an Executive
        effective_from: the date this version of the position was either declared in the Constitution or the first time this version had someone using it
        effective_to: the date this version of the position was not used, either from the role being eliminated or the constraints on the position were modified
    """

    __tablename__ = "officer_position_version"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    position_id: Mapped[int] = mapped_column(
        ForeignKey("officer_position.id"),
    )

    position: Mapped[OfficerPositionDB] = relationship()

    type: Mapped[OfficerPositionTypeEnum] = mapped_column(
        Enum(
            OfficerPositionTypeEnum,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [category.value for category in enum],
            name="type_valid",
        ),
    )

    multiple_allowed: Mapped[bool | None] = mapped_column(
        nullable=True,
    )

    effective_from: Mapped[date] = mapped_column(Date)

    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="effective_end_after_start",
        ),
        CheckConstraint(
            "CASE "
            "WHEN type = 'executive' THEN multiple_allowed IS NOT NULL "
            "WHEN type IN ('elected_representative', 'appointed_representative') "
            "THEN multiple_allowed IS NULL "
            "ELSE FALSE END",
            name="multiple_allowed_by_category",
        ),
        ExcludeConstraint(
            (position_id, "="),
            (
                func.daterange(effective_from, effective_to, "[]"),
                "&&",
            ),
            using="gist",
            name="no_overlapping_versions",
        ),
    )


class OfficerTermDB(Base):
    """
    A row represents an assignment of a person to a position.

    Attributes:
        __tablename__: officer_term
        id: unique ID
        officer_id: officer_info.id of this term
        position_version_id: officer_position_version.id of this term
        position_version: use `joinedload()` to get the string representation of the position
        start_date: start date of the term
        end_date: end date of the term
        photo_url: URL of the officer's photo for this term
    """

    __tablename__ = "officer_term"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    officer_id: Mapped[int] = mapped_column(
        ForeignKey("officer_info.id"),
    )

    position_version_id: Mapped[int] = mapped_column(
        ForeignKey("officer_position_version.id"),
    )

    position_version: Mapped[OfficerPositionVersionDB] = relationship()

    start_date: Mapped[date] = mapped_column(Date)

    # end_date is only not-specified for positions that don't have a length (ie. webmaster)
    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    photo_url: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )  # some urls get big, best to let it be a string

    officer: Mapped[OfficerInfoDB] = relationship(
        back_populates="terms",
    )

    __table_args__ = (CheckConstraint("end_date IS NULL OR end_date >= start_date", name="end_after_start"),)

    # Triggers
    # An Officer Term must fall entirely within the effective period of its referenced Position Version.
    # An Officer cannot have overlapping Officer Terms where both Position Versions are categorized as executive.
    # If a Position Version is categorized as executive and has multiple_allowed = false, there cannot be another overlapping Officer Term referencing a version of the same underlying Position.


class OfficerTermDataDB(Base):
    """
    Defines legacy data that is not collected or presented much anymore, but is kept for historical reasons.

    Attributes:
        __tablename__: officer_term_data
        id: the officer term ID this is linked to
        favourite_course_0: first favourite course
        favourite_course_1: second favourite course
        favourite_pl_0: first favourite programming language
        favourite_pl_1: second favourite programming language
        biography: blurb about the officer
    """

    __tablename__ = "officer_term_data"

    id: Mapped[int] = mapped_column(
        ForeignKey("officer_term.id"),
        primary_key=True,
    )

    favourite_course_0: Mapped[str | None] = mapped_column(
        String(TERM_DATA_COURSE_MAX_LEN),
        nullable=True,
    )

    favourite_course_1: Mapped[str | None] = mapped_column(
        String(TERM_DATA_COURSE_MAX_LEN),
        nullable=True,
    )

    # programming language
    favourite_pl_0: Mapped[str | None] = mapped_column(
        String(TERM_DATA_PL_MAX_LEN),
        nullable=True,
    )

    favourite_pl_1: Mapped[str | None] = mapped_column(
        String(TERM_DATA_PL_MAX_LEN),
        nullable=True,
    )

    biography: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
