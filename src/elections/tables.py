from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    Text,
)

from constants import (
    COMPUTING_ID_LEN,
    DISCORD_ID_LEN,
    DISCORD_NAME_LEN,
    DISCORD_NICKNAME_LEN,
)
from database import Base
from officers.constants import COUNCIL_REP_ELECTION_POSITIONS, GENERAL_ELECTION_POSITIONS

# If you wish to add more elections & defaults, please see `create_election`
election_types = ["general_election", "by_election", "council_rep_election"]

DEFAULT_POSITIONS_GENERAL_ELECTION = ",".join(GENERAL_ELECTION_POSITIONS)
DEFAULT_POSITIONS_BY_ELECTION = ",".join(GENERAL_ELECTION_POSITIONS)
DEFAULT_POSITIONS_COUNCIL_REP_ELECTION = ",".join(COUNCIL_REP_ELECTION_POSITIONS)

STATUS_BEFORE_NOMINATIONS = "before_nominations"
STATUS_NOMINATIONS = "nominations"
STATUS_VOTING = "voting"
STATUS_AFTER_VOTING = "after_voting"

MAX_ELECTION_NAME = 64
MAX_ELECTION_SLUG = 64

class Election(Base):
    __tablename__ = "election"

    # Slugs are unique identifiers
    slug = Column(String(MAX_ELECTION_SLUG), primary_key=True)
    name = Column(String(MAX_ELECTION_NAME), nullable=False)
    type = Column(String(64), default="general_election")
    datetime_start_nominations = Column(DateTime, nullable=False)
    datetime_start_voting = Column(DateTime, nullable=False)
    datetime_end_voting = Column(DateTime, nullable=False)

    # a csv list of positions which must be elements of OfficerPosition
    avaliable_positions = Column(Text, nullable=False)
    survey_link = Column(String(300))

    def private_details(self, at_time: datetime) -> dict:
        # is serializable
        return {
            "slug": self.slug,
            "name": self.name,
            "type": self.type,

            "datetime_start_nominations": self.datetime_start_nominations.isoformat(),
            "datetime_start_voting": self.datetime_start_voting.isoformat(),
            "datetime_end_voting": self.datetime_end_voting.isoformat(),

            "status": self.status(at_time),
            "avaliable_positions": self.avaliable_positions,
            "survey_link": self.survey_link,
        }

    def public_details(self, at_time: datetime) -> dict:
        # is serializable
        return {
            "slug": self.slug,
            "name": self.name,
            "type": self.type,

            "datetime_start_nominations": self.datetime_start_nominations.isoformat(),
            "datetime_start_voting": self.datetime_start_voting.isoformat(),
            "datetime_end_voting": self.datetime_end_voting.isoformat(),

            "status": self.status(at_time),
            "avaliable_positions": self.avaliable_positions,
        }

    def public_metadata(self, at_time: datetime) -> dict:
        # is serializable
        return {
            "slug": self.slug,
            "name": self.name,
            "type": self.type,

            "datetime_start_nominations": self.datetime_start_nominations.isoformat(),
            "datetime_start_voting": self.datetime_start_voting.isoformat(),
            "datetime_end_voting": self.datetime_end_voting.isoformat(),

            "status": self.status(at_time),
        }

    def to_update_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "type": self.type,

            "datetime_start_nominations": self.datetime_start_nominations,
            "datetime_start_voting": self.datetime_start_voting,
            "datetime_end_voting": self.datetime_end_voting,

            "avaliable_positions": self.avaliable_positions,
            "survey_link": self.survey_link,
        }

    def status(self, at_time: datetime) -> str:
        if at_time <= self.datetime_start_nominations:
            return STATUS_BEFORE_NOMINATIONS
        elif at_time <= self.datetime_start_voting:
            return STATUS_NOMINATIONS
        elif at_time <= self.datetime_end_voting:
            return STATUS_VOTING
        else:
            return STATUS_AFTER_VOTING

class NomineeInfo(Base):
    __tablename__ = "election_nominee_info"

    computing_id = Column(String(COMPUTING_ID_LEN), primary_key=True)
    full_name = Column(String(64), nullable=False)
    linked_in = Column(String(128))
    instagram = Column(String(128))
    email = Column(String(64))
    #discord = Column(String(DISCORD_NAME_LEN))
    #discord_id = Column(String(DISCORD_ID_LEN))
    discord_username = Column(String(DISCORD_NICKNAME_LEN))

    def to_update_dict(self) -> dict:
        return {
            "computing_id": self.computing_id,
            "full_name": self.full_name,

            "linked_in": self.linked_in,
            "instagram": self.instagram,
            "email": self.email,
            "discord_username": self.discord_username,
        }

    def as_serializable(self) -> dict:
        # NOTE: this function is currently the same as to_update_dict since the contents
        # have a different invariant they're upholding, which may cause them to change if a
        # new property is introduced. For example, dates must be converted into strings
        # to be serialized, but must not for update dictionaries.
        return {
            "computing_id": self.computing_id,
            "full_name": self.full_name,

            "linked_in": self.linked_in,
            "instagram": self.instagram,
            "email": self.email,
            "discord_username": self.discord_username,
        }

class NomineeApplication(Base):
    __tablename__ = "election_nominee_application"

    # TODO: add index for nominee_election?
    computing_id = Column(ForeignKey("election_nominee_info.computing_id"), primary_key=True)
    nominee_election = Column(ForeignKey("election.slug"), primary_key=True)
    position = Column(String(64), primary_key=True)

    speech = Column(Text)

    __table_args__ = (
        PrimaryKeyConstraint(computing_id, nominee_election, position),
    )

    def serializable_dict(self) -> dict:
        return {
            "computing_id": self.computing_id,
            "nominee_election": self.nominee_election,
            "position": self.position,

            "speech": self.speech,
        }

    def to_update_dict(self) -> dict:
        return {
            "computing_id": self.computing_id,
            "nominee_election": self.nominee_election,
            "position": self.position,

            "speech": self.speech,
        }

