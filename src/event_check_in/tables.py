from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


# Each row defines a checkin period, separate from individual attendance records
class EventCheckInDB(Base):
    __tablename__ = "event_check_in"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    event_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("event_info.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(64))

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
    )

    opens_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closes_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # SQLAlchemy supplies this timestamp when it emits an update for the configuration
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Enforce time ordering in PostgreSQL as well as in request validation
    __table_args__ = (
        CheckConstraint(
            "closes_at IS NULL OR opens_at IS NULL OR closes_at > opens_at",
            name="closes_after_opens",
        ),
    )
