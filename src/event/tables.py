from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from event.constants import EventFrequencyEnum


class EventDB(Base):
    __tablename__ = "event_info"

    eid: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(String(64))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    frequency: Mapped[EventFrequencyEnum] = mapped_column(String(64), server_default=text("'NONE'"), nullable=True)
    repeat_start_date: Mapped[date] = mapped_column(Date, nullable=True)
    repeat_end_date: Mapped[date] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("start_time < end_time", name="check_start_time_before_end_time"),
        CheckConstraint("repeat_start_date < repeat_end_date", name="check_repeat_start_date_before_repeat_end_date"),
        CheckConstraint(frequency.in_([e.value for e in EventFrequencyEnum]), name="valid_frequency_value")
    )
