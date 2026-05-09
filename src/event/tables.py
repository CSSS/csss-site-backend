from sqlalchemy import (
    String,
    DateTime,
    Text,
)
from sqlalchemy.org import Mapped, mapped_column

from database import Base
import datetime

class EventDB(Base):
    __tablename__ = "event_info"

    eid: Mapped[int] = mapped_column(
        int, 
        primary_key=True
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True
    )
    name: Mapped[str] = mapped_column(String(64))
    start_time: Mapped[datetime.datetime()] = mapped_column(DateTime)
    end_time: Mapped[datetime.datetime()] = mapped_column(DateTime)
    repeat: Mapped[str] = mapped_column(String(64))
    start_date: Mapped[datetime.date()] = mapped_column(
        Date,
        nullable=True
    )
    end_date: Mapped[datetime.date()] = mapped_column(
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

    