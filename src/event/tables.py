from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Integer, Text, Uuid, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from event.constants import EventFrequencyEnum, EventStatusEnum


class EventDB(Base):
    __tablename__ = "event_info"

    eid: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    group_id: Mapped[UUID] = mapped_column(Uuid, nullable=True)
    location: Mapped[str] = mapped_column(Text, nullable=True)
    organizer: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[EventStatusEnum] = mapped_column(
        Enum(
            EventStatusEnum,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [status.value for status in enum],
            name="valid_status"
        )
    )
    url: Mapped[str] = mapped_column(Text, nullable=True)
    image_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("image_asset.image_id"),
        nullable=True
        )

    __table_args__ = (
        CheckConstraint("start_datetime <= end_datetime", name="check_start_time_before_end_time"),
    )
