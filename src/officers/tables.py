from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from constants import (
    COMPUTING_ID_LEN,
    DISCORD_ID_LEN,
    DISCORD_NAME_LEN,
    DISCORD_NICKNAME_LEN,
    GITHUB_USERNAME_LEN,
)
from database import Base
from officers.constants import OfficerPositionEnum


# A row represents an assignment of a person to a position.
# An officer with multiple positions, such as Frosh Chair & DoE, is broken up into multiple assignments.
class OfficerTerm(Base):
    __tablename__ = "officer_term"

    id: Mapped[str] = mapped_column(Integer, primary_key=True, autoincrement=True)

    computing_id: Mapped[str] = mapped_column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id"),
        nullable=False,
    )

    position: Mapped[OfficerPositionEnum] = mapped_column(String(128), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # end_date is only not-specified for positions that don't have a length (ie. webmaster)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    nickname: Mapped[str] = mapped_column(String(128), nullable=True)
    favourite_course_0: Mapped[str] = mapped_column(String(64), nullable=True)
    favourite_course_1: Mapped[str] = mapped_column(String(64), nullable=True)
    # programming language
    favourite_pl_0: Mapped[str] = mapped_column(String(64), nullable=True)
    favourite_pl_1: Mapped[str] = mapped_column(String(64), nullable=True)
    biography: Mapped[str] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str] = mapped_column(Text, nullable=True) # some urls get big, best to let it be a string

    __table_args__ = (UniqueConstraint("computing_id", "position", "start_date"),) # This needs a comma to work

    def serializable_dict(self) -> dict:
        return {
            "id": self.id,
            "computing_id": self.computing_id,

            "position": self.position,
            "start_date": self.start_date.isoformat() if self.start_date is not None else None,
            "end_date": self.end_date.isoformat() if self.end_date is not None else None,

            "nickname": self.nickname,
            "favourite_course_0": self.favourite_course_0,
            "favourite_course_1": self.favourite_course_1,
            "favourite_pl_0": self.favourite_pl_0,
            "favourite_pl_1": self.favourite_pl_1,
            "biography": self.biography,
            "photo_url": self.photo_url,
        }

    def is_filled_in(self):
        return (
            # photo & end_date don't have to be uploaded for the term to be "filled"
            # NOTE: this definition might have to be updated
            self.computing_id is not None
            and self.start_date is not None
            and self.nickname is not None
            and self.favourite_course_0 is not None
            and self.favourite_course_1 is not None
            and self.favourite_pl_0 is not None
            and self.favourite_pl_1 is not None
            and self.biography is not None
        )

    def to_update_dict(self) -> dict:
        return {
            "computing_id": self.computing_id,

            "position": self.position,
            "start_date": self.start_date,
            "end_date": self.end_date,

            "nickname": self.nickname,
            "favourite_course_0": self.favourite_course_0,
            "favourite_course_1": self.favourite_course_1,
            "favourite_pl_0": self.favourite_pl_0,
            "favourite_pl_1": self.favourite_pl_1,
            "biography": self.biography,
            "photo_url": self.photo_url,
        }

# this table contains information that we only need a most up-to-date version of, and
# don't need to keep a history of. However, it also can't be easily updated.
class OfficerInfo(Base):
    __tablename__ = "officer_info"

    computing_id: Mapped[str] = mapped_column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id"),
        primary_key=True,
    )

    # TODO (#71): we'll need to use SFU's API to get the legal name for users
    legal_name: Mapped[str] = mapped_column(String(128), nullable=False) # some people have long names, you never know
    phone_number: Mapped[str] = mapped_column(String(24), nullable=True)

    # TODO (#99): add unique constraints to discord_id (stops users from stealing the username of someone else)
    discord_id: Mapped[str] = mapped_column(String(DISCORD_ID_LEN), nullable=True)
    discord_name: Mapped[str] = mapped_column(String(DISCORD_NAME_LEN), nullable=True)
    # this is their nickname in the csss server
    discord_nickname: Mapped[str] = mapped_column(String(DISCORD_NICKNAME_LEN), nullable=True)

    # Technically 320 is the most common max-size for emails, but we'll use 256 instead,
    # since it's reasonably large (input validate this too)
    # TODO (#99): add unique constraint to this (stops users from stealing the username of someone else)
    google_drive_email: Mapped[str] = mapped_column(String(256), nullable=True)

    # TODO (#99): add unique constraint to this (stops users from stealing the username of someone else)
    github_username: Mapped[str] = mapped_column(String(GITHUB_USERNAME_LEN), nullable=True)

    # TODO (#22): add support for giving executives bitwarden access automagically
    # has_signed_into_bitwarden: Mapped[str] = mapped_column(Boolean)

    def serializable_dict(self) -> dict:
        return {
            "is_filled_in": self.is_filled_in(),

            "legal_name": self.legal_name,
            "discord_id": self.discord_id,
            "discord_name": self.discord_name,
            "discord_nickname": self.discord_nickname,

            "computing_id": self.computing_id,
            "phone_number": self.phone_number,
            "github_username": self.github_username,

            "google_drive_email": self.google_drive_email,
        }

    def is_filled_in(self):
        return (
            self.computing_id is not None
            and self.legal_name is not None
            and self.phone_number is not None
            and self.discord_id is not None
            and self.discord_name is not None
            and self.discord_nickname is not None
            and self.google_drive_email is not None
            and self.github_username is not None
        )

    def to_update_dict(self) -> dict:
        return {
            # TODO (#71): if the API call to SFU's api to get legal name fails, we want to fail & not insert the entry.
            # for now, we should insert a default value
            "legal_name": "default name" if self.legal_name is None else self.legal_name,

            "discord_id": self.discord_id,
            "discord_name": self.discord_name,
            "discord_nickname": self.discord_nickname,

            "phone_number": self.phone_number,
            "github_username": self.github_username,
            "google_drive_email": self.google_drive_email,
        }
