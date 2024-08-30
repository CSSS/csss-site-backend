from __future__ import annotations

# from sqlalchemy.orm import relationship
from constants import (
    COMPUTING_ID_LEN,
    DISCORD_ID_LEN,
    DISCORD_NAME_LEN,
    DISCORD_NICKNAME_LEN,
    GITHUB_USERNAME_LEN,
)
from database import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)

from officers.types import OfficerInfoData, OfficerTermData


# A row represents an assignment of a person to a position.
# An officer with multiple positions, such as Frosh Chair & DoE, is broken up into multiple assignments.
class OfficerTerm(Base):
    __tablename__ = "officer_term"

    id = Column(Integer, primary_key=True, autoincrement=True)
    computing_id = Column(
        String(COMPUTING_ID_LEN),
        nullable=False,
    )

    # a record will only be set as publically visible if sufficient data has been given
    is_filled_in = Column(Boolean, nullable=False)

    position = Column(String(128), nullable=False)
    start_date = Column(DateTime, nullable=False)
    # end_date is only not-specified for positions that don't have a length (ie. webmaster)
    end_date = Column(DateTime)

    nickname = Column(String(128))
    favourite_course_0 = Column(String(32))
    favourite_course_1 = Column(String(32))
    # programming language
    favourite_pl_0 = Column(String(32))
    favourite_pl_1 = Column(String(32))
    biography = Column(Text)
    photo_url = Column(Text)  # some urls get big, best to let it be a string

    @staticmethod
    def from_data(is_filled_in: bool, officer_term_data: OfficerTermData) -> OfficerTerm:
        return OfficerTerm(
            computing_id = officer_term_data.computing_id,
            is_filled_in = is_filled_in,

            position = officer_term_data.position,
            start_date = officer_term_data.start_date,
            end_date = officer_term_data.end_date,

            nickname = officer_term_data.nickname,
            favourite_course_0 = officer_term_data.favourite_course_0,
            favourite_course_1 = officer_term_data.favourite_course_1,
            favourite_pl_0 = officer_term_data.favourite_pl_0,
            favourite_pl_1 = officer_term_data.favourite_pl_1,
            biography = officer_term_data.biography,
            photo_url = officer_term_data.photo_url,
        )

    @staticmethod
    def update_dict(is_filled_in: bool, officer_term_data: OfficerTermData) -> dict:
        # cannot update:
        # - computing_id
        # - start_date
        # - position
        return {
            "is_filled_in": is_filled_in,

            "end_date": officer_term_data.end_date,
            "nickname": officer_term_data.nickname,

            "favourite_course_0": officer_term_data.favourite_course_0,
            "favourite_course_1": officer_term_data.favourite_course_1,
            "favourite_pl_0": officer_term_data.favourite_pl_0,
            "favourite_pl_1": officer_term_data.favourite_pl_1,

            "biography": officer_term_data.biography,
            "photo_url": officer_term_data.photo_url,
        }

    def serializable_dict(self) -> dict:
        return {
            "id": self.id,
            "computing_id": self.computing_id,

            "is_filled_in": self.is_filled_in,

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

# this table contains information that we only need a most up-to-date version of, and
# don't need to keep a history of. However, it also can't be easily updated.
class OfficerInfo(Base):
    __tablename__ = "officer_info"

    is_filled_in = Column(Boolean, nullable=False)
    # TODO: we'll need to use SFU's API to get the legal name for users
    legal_name = Column(String(128), nullable=False)  # some people have long names, you never know

    # a null discord id would mean you don't have discord
    discord_id = Column(String(DISCORD_ID_LEN))
    discord_name = Column(String(DISCORD_NAME_LEN))
    # this is their nickname in the csss server
    discord_nickname = Column(String(DISCORD_NICKNAME_LEN))

    # private info will be added last
    computing_id = Column(
        String(COMPUTING_ID_LEN),
        primary_key=True,
    )
    phone_number = Column(String(24))
    # TODO: add unique constraint to this (stops users from stealing the username of someone else)
    github_username = Column(String(GITHUB_USERNAME_LEN))

    # A comma separated list of emails
    # technically 320 is the most common max-size for emails
    # specifications for valid email addresses vary widely, but we will not
    # accept any that contain a comma
    google_drive_email = Column(Text)

    # NOTE: not sure if we'll need this, depending on implementation
    # has_signed_into_bitwarden = Column(Boolean)

    # TODO: can we represent more complicated data structures?
    # has_autheticated_github = Column(Boolean)

    @staticmethod
    def from_data(is_filled_in: bool, officer_info_data: OfficerInfoData) -> OfficerTerm:
        return OfficerInfo(
            is_filled_in = is_filled_in,
            legal_name = officer_info_data.legal_name,

            discord_id = officer_info_data.discord_id,
            discord_name = officer_info_data.discord_name,
            discord_nickname = officer_info_data.discord_nickname,

            computing_id = officer_info_data.computing_id,
            phone_number = officer_info_data.phone_number,
            github_username = officer_info_data.github_username,

            google_drive_email = officer_info_data.google_drive_email,
        )

    @staticmethod
    def update_dict(is_filled_in: bool, officer_info_data: OfficerInfoData) -> dict:
        # should only NOT contain the pkey (computing_id)
        return {
            "is_filled_in": is_filled_in,

            # TODO: if the API call to SFU's api to get legal name fails, we want to fail & not insert the entry.
            # for now, we should insert a default value
            "legal_name": "default name" if officer_info_data.legal_name is None else officer_info_data.legal_name,
            "discord_id": officer_info_data.discord_id,
            "discord_name": officer_info_data.discord_name,
            "discord_nickname": officer_info_data.discord_nickname,

            "phone_number": officer_info_data.phone_number,
            "github_username": officer_info_data.github_username,
            "google_drive_email": officer_info_data.google_drive_email,
        }
