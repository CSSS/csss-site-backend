from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from elections.models import (
    ElectionStatusEnum,
    ElectionTypeEnum,
    ElectionUpdateParams,
)
from officers.constants import OfficerPositionEnum
from utils.types import StringList

MAX_ELECTION_NAME = 64
MAX_ELECTION_SLUG = 64

class Election(Base):
    __tablename__ = "election"

    # Slugs are unique identifiers
    slug: Mapped[str] = mapped_column(String(MAX_ELECTION_SLUG), primary_key=True)
    name: Mapped[str] = mapped_column(String(MAX_ELECTION_NAME), nullable=False)
    type: Mapped[ElectionTypeEnum] = mapped_column(String(32), default=ElectionTypeEnum.GENERAL)
    datetime_start_nominations: Mapped[datetime] = mapped_column(Date, nullable=False)
    datetime_start_voting: Mapped[datetime] = mapped_column(Date, nullable=False)
    datetime_end_voting: Mapped[datetime] = mapped_column(Date, nullable=False)

    # a comma-separated string of positions which must be elements of OfficerPosition
    # By giving it the type `StringList`, the database entry will automatically be marshalled to the correct form
    # DB -> Python: str -> list[str]
    # Python -> DB: list[str] -> str
    available_positions: Mapped[list[OfficerPositionEnum]] = mapped_column(StringList(), nullable=False,)
    survey_link: Mapped[str | None] = mapped_column(String(300))

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
            "available_positions": self.available_positions,
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
            "available_positions": self.available_positions,
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

            "available_positions": self.available_positions,
            "survey_link": self.survey_link,
        }

    def update_from_params(self, params: ElectionUpdateParams):
        update_data = params.model_dump(
            exclude_unset=True,
            exclude={"datetime_start_nominations", "datetime_start_voting", "datetime_end_voting"}
        )
        for k, v in update_data.items():
            setattr(self, k, v)
        if params.datetime_start_nominations:
            self.datetime_start_nominations = datetime.fromisoformat(params.datetime_start_nominations)
        if params.datetime_start_voting:
            self.datetime_start_voting = datetime.fromisoformat(params.datetime_start_voting)
        if params.datetime_end_voting:
            self.datetime_end_voting = datetime.fromisoformat(params.datetime_end_voting)

    def status(self, at_time: datetime) -> str:
        if at_time <= self.datetime_start_nominations:
            return ElectionStatusEnum.BEFORE_NOMINATIONS
        elif at_time <= self.datetime_start_voting:
            return ElectionStatusEnum.NOMINATIONS
        elif at_time <= self.datetime_end_voting:
            return ElectionStatusEnum.VOTING
        else:
            return ElectionStatusEnum.AFTER_VOTING

