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

election_types = ["general_election", "by_election", "council_rep_election"]

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
    survey_link = Column(String(300))

    def serializable_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "type": self.type,

            "datetime_start_nominations": self.datetime_start_nominations.isoformat(),
            "datetime_start_voting": self.datetime_start_voting.isoformat(),
            "datetime_end_voting": self.datetime_end_voting.isoformat(),

            "survey_link": self.survey_link,
        }

    def public_details(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "type": self.type,

            "datetime_start_nominations": self.datetime_start_nominations.isoformat(),
            "datetime_start_voting": self.datetime_start_voting.isoformat(),
            "datetime_end_voting": self.datetime_end_voting.isoformat(),
        }

    def to_update_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "type": self.type,

            "datetime_start_nominations": self.datetime_start_nominations,
            "datetime_start_voting": self.datetime_start_voting,
            "datetime_end_voting": self.datetime_end_voting,

            "survey_link": self.survey_link,
        }

# Each row represents a nominee of a given election
class Nominee(Base):
    __tablename__ = "election_nominee"

    # Previously named sfuid
    computing_id = Column(String(COMPUTING_ID_LEN), primary_key=True)
    full_name = Column(String(64), nullable=False)
    facebook = Column(String(128))
    instagram = Column(String(128))
    email = Column(String(64))
    discord = Column(String(DISCORD_NAME_LEN))
    discord_id = Column(String(DISCORD_ID_LEN))
    discord_username = Column(String(DISCORD_NICKNAME_LEN))

class NomineeApplication(Base):
    __tablename__ = "nominee_application"

    computing_id = Column(ForeignKey("election_nominee.computing_id"), primary_key=True)
    nominee_election = Column(ForeignKey("election.slug"), primary_key=True)
    speech = Column(Text)
    position = Column(String(64), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(computing_id, nominee_election),
    )
