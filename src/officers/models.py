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


# a row represents an assignment of a person to a position
# an officer with multiple positions, such as Frosh Chair & DoE, is broken up into multiple assignments
class OfficerTerm(Base):
    __tablename__ = "officer_term"

    id = Column(Integer, primary_key=True)
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

    # Each row is information that *might* get updated each term.
    # TODO: Officers can also edit their entries each semester, but not past semesters. History
    # is not saved, so changes are lost.

    nickname = Column(String(128))
    favourite_course_0 = Column(String(32))
    favourite_course_1 = Column(String(32))
    # programming language
    favourite_pl_0 = Column(String(32))
    favourite_pl_1 = Column(String(32))
    biography = Column(Text)
    photo_url = Column(Text)  # some urls get big, best to let it be a string


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
