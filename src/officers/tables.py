from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Select,
    String,
    Text,
    and_,
)

# from sqlalchemy.orm import relationship
from constants import (
    COMPUTING_ID_LEN,
    DISCORD_ID_LEN,
    DISCORD_NAME_LEN,
    DISCORD_NICKNAME_LEN,
    GITHUB_USERNAME_LEN,
)
from database import Base


# A row represents an assignment of a person to a position.
# An officer with multiple positions, such as Frosh Chair & DoE, is broken up into multiple assignments.
class OfficerTerm(Base):
    __tablename__ = "officer_term"

    id = Column(Integer, primary_key=True, autoincrement=True)
    computing_id = Column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id"),
        nullable=False,
    )

    position = Column(String(128), nullable=False)
    # TODO: replace these with Date, not Datetime
    start_date = Column(DateTime, nullable=False)
    # end_date is only not-specified for positions that don't have a length (ie. webmaster)
    end_date = Column(DateTime, nullable=True)

    nickname = Column(String(128), nullable=True)
    favourite_course_0 = Column(String(32), nullable=True)
    favourite_course_1 = Column(String(32), nullable=True)
    # programming language
    favourite_pl_0 = Column(String(32), nullable=True)
    favourite_pl_1 = Column(String(32), nullable=True)
    biography = Column(Text, nullable=True)
    photo_url = Column(Text, nullable=True) # some urls get big, best to let it be a string

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

    # a record will only be publically visible if sufficient data has been given
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

    @staticmethod
    def sql_is_filled_in(query: Select) -> Select:
        """Should be identical to self.is_filled_in()"""
        return query.where(
            and_(
                OfficerTerm.computing_id is not None,
                OfficerTerm.start_date is not None,
                OfficerTerm.nickname is not None,
                OfficerTerm.favourite_course_0 is not None,
                OfficerTerm.favourite_course_1 is not None,
                OfficerTerm.favourite_pl_0 is not None,
                OfficerTerm.favourite_pl_1 is not None,
                OfficerTerm.biography is not None,
            )
        )

    def to_update_dict(self) -> dict:
        return {
            # TODO: do we want computing_id to be changeable?
            # "computing_id": self.computing_id,

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

    computing_id = Column(
        String(COMPUTING_ID_LEN),
        ForeignKey("site_user.computing_id"),
        primary_key=True,
    )

    # TODO: we'll need to use SFU's API to get the legal name for users
    legal_name = Column(String(128), nullable=False) # some people have long names, you never know
    phone_number = Column(String(24), nullable=True)

    # a null discord id would mean you don't have discord
    # TODO: add unique constraints to these (stops users from stealing the username of someone else)
    discord_id = Column(String(DISCORD_ID_LEN), nullable=True)
    discord_name = Column(String(DISCORD_NAME_LEN), nullable=True)
    # this is their nickname in the csss server
    discord_nickname = Column(String(DISCORD_NICKNAME_LEN), nullable=True)

    # Technically 320 is the most common max-size for emails, but we'll use 256 instead,
    # since it's reasonably large (input validate this too)
    # TODO: add unique constraint to this (stops users from stealing the username of someone else)
    google_drive_email = Column(String(256), nullable=True)

    # TODO: add unique constraint to this (stops users from stealing the username of someone else)
    github_username = Column(String(GITHUB_USERNAME_LEN), nullable=True)

    # NOTE: not sure if we'll need this, depending on implementation
    # TODO: get this data on the fly when requested, but rate limit users
    # to something like 1/s 100/hour
    # has_signed_into_bitwarden = Column(Boolean)

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
            # TODO: if the API call to SFU's api to get legal name fails, we want to fail & not insert the entry.
            # for now, we should insert a default value
            "legal_name": "default name" if self.legal_name is None else self.legal_name,

            "discord_id": self.discord_id,
            "discord_name": self.discord_name,
            "discord_nickname": self.discord_nickname,

            "phone_number": self.phone_number,
            "github_username": self.github_username,
            "google_drive_email": self.google_drive_email,
        }
