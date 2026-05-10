from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Text,
    Date
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from datetime import datetime, date

class EventDB(Base):
    __tablename__ = "event_info"

    eid: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True,
        autoincrement=True
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(64))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    repeat: Mapped[str] = mapped_column(String(64))
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=True
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=True
    )

    def serialize(self) -> dict:
        return{
            "eid": self.eid,
            "name": self.name,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.start_time,
            "start_date": self.start_time,
            "end_date": self.start_time,
        }

    