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


# Each row represents an instance of an
class Election(Base):
    __tablename__ = "election"

    # Slugs are unique identifiers
    slug = Column(String(32), primary_key=True)
    name = Column(String(32), nullable=False)
    officer_id = Column(String(COMPUTING_ID_LEN), nullable=False)
    # Can be one of (general_election: General Election, by_election: By-Election, council_rep_election: Council Rep Election)
    type = Column(String(64), default="general_election")
    date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    websurvey = Column(String(300))

# Each row represents a nominee of a given election
class Nominee(Base):
    __tablename__ = "election_nominee"

    # Previously named sfuid
    computing_id = Column(String(COMPUTING_ID_LEN), primary_key=True)
    full_name = Column(String(64), nullable=False)
    facebook = Column(String(64))
    instagram = Column(String(64))
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
