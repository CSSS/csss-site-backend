from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    Text,
)
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.attributes import set_attribute
from sqlalchemy.util import hybridproperty

from constants import (
    COMPUTING_ID_LEN,
    DISCORD_NICKNAME_LEN,
)
from database import Base
from elections.models import (
    ElectionStatusEnum,
    ElectionUpdateParams,
    NomineeApplicationUpdateParams,
    NomineeUpdateParams,
)
from officers.types import OfficerPositionEnum

MAX_ELECTION_NAME = 64
MAX_ELECTION_SLUG = 64

class Election(Base):
    __tablename__ = "election"

    # Slugs are unique identifiers
    slug: Mapped[str] = mapped_column(String(MAX_ELECTION_SLUG), primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_ELECTION_NAME), nullable=False)
    type: Mapped[str] = mapped_column(String(64), default="general_election")
    datetime_start_nominations: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    datetime_start_voting: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    datetime_end_voting: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # a csv list of positions which must be elements of OfficerPosition
    _available_positions: Mapped[str] = mapped_column("available_positions", Text, nullable=False)
    survey_link: Mapped[str | None] = mapped_column(String(300))

    @hybrid_property
    def available_positions(self) -> str: # pyright: ignore
        return self._available_positions

    @available_positions.setter
    def available_positions(self, value: str | list[str]) -> None:
        if isinstance(value, list):
            value = ",".join(value)
        self._available_positions = value


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
            "available_positions": self._available_positions,
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
            "available_positions": self._available_positions,
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

            "available_positions": self._available_positions,
            "survey_link": self.survey_link,
        }

    def update_from_params(self, params: ElectionUpdateParams):
        update_data = params.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(self, k, v)

    def status(self, at_time: datetime) -> str:
        if at_time <= self.datetime_start_nominations:
            return ElectionStatusEnum.BEFORE_NOMINATIONS
        elif at_time <= self.datetime_start_voting:
            return ElectionStatusEnum.NOMINATIONS
        elif at_time <= self.datetime_end_voting:
            return ElectionStatusEnum.VOTING
        else:
            return ElectionStatusEnum.AFTER_VOTING

class NomineeInfo(Base):
    __tablename__ = "election_nominee_info"

    computing_id: Mapped[str] = mapped_column(String(COMPUTING_ID_LEN), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(64), nullable=False)
    linked_in: Mapped[str] = mapped_column(String(128))
    instagram: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(64))
    discord_username: Mapped[str] = mapped_column(String(DISCORD_NICKNAME_LEN))

    def to_update_dict(self) -> dict:
        return {
            "computing_id": self.computing_id,
            "full_name": self.full_name,

            "linked_in": self.linked_in,
            "instagram": self.instagram,
            "email": self.email,
            "discord_username": self.discord_username,
        }

    def serialize(self) -> dict:
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

    computing_id: Mapped[str] = mapped_column(ForeignKey("election_nominee_info.computing_id"), primary_key=True)
    nominee_election: Mapped[str] = mapped_column(ForeignKey("election.slug"), primary_key=True)
    position: Mapped[OfficerPositionEnum] = mapped_column(String(64), primary_key=True)

    speech: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        PrimaryKeyConstraint(computing_id, nominee_election, position),
    )

    def serialize(self) -> dict:
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

    def update_from_params(self, params: NomineeApplicationUpdateParams):
        update_data = params.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(self, k, v)


