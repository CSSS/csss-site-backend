from sqlalchemy import (
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from constants import (
    COMPUTING_ID_LEN,
    DISCORD_NICKNAME_LEN,
)
from database import Base


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

