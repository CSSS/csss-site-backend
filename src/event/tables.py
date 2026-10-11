from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from ulid import ULID

from constants import ULID_MAX_LEN
from database import Base
from event.constants import EventStatusEnum


class EventDB(Base):
    """

    Attributes:
        __tablename__: event_info
        id: Internal unique ID
        eid: Public unique ID
        description: description of the event
        name: name of the event
        start_datetime: start date and time of the event
        end_datetime: end date and time of the event
        group_id: the group this event is a part of
        location: a string representing the location of the event
        organizer: the group/individuals who organized the event
        status: the status of the event
        url: a URL to something related to the event (e.g. a registration page or marketing site)
        image_id: the ID of the image associated with this event, i.e. its poster
    """

    __tablename__ = "event_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    eid: Mapped[str] = mapped_column(String(ULID_MAX_LEN), unique=True, default=lambda: str(ULID()))

    description: Mapped[str] = mapped_column(Text)

    name: Mapped[str] = mapped_column(Text)

    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    group_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)

    location: Mapped[str | None] = mapped_column(Text, nullable=True)

    organizer: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[EventStatusEnum] = mapped_column(
        Enum(
            EventStatusEnum,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [status.value for status in enum],
            name="valid_status",
        )
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    image_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("image_asset.image_id"), nullable=True)

    __table_args__ = (
        CheckConstraint("start_datetime <= end_datetime", name="check_start_datetime_before_end_datetime"),
    )
