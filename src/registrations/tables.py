from sqlalchemy import ForeignKey, PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from officers.constants import OfficerPositionEnum
from registrations.models import NomineeApplicationUpdate


class NomineeApplicationDB(Base):
    __tablename__ = "election_nominee_application"

    computing_id: Mapped[str] = mapped_column(ForeignKey("election_nominee_info.computing_id"), primary_key=True)
    nominee_election: Mapped[str] = mapped_column(ForeignKey("election.slug"), primary_key=True)
    position: Mapped[OfficerPositionEnum] = mapped_column(String(64), primary_key=True)

    speech: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (PrimaryKeyConstraint(computing_id, nominee_election, position),)

    def serialize(self) -> dict:
        return {
            "computing_id": self.computing_id,
            "nominee_election": self.nominee_election,
            "position": self.position,
            "speech": self.speech,
        }

    def update_from_params(self, params: NomineeApplicationUpdate):
        update_data = params.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(self, k, v)
