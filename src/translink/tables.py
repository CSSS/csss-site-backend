from datetime import date, datetime

from sqlalchemy import DateTime, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TransLinkStaticScheduleDB(Base):
    __tablename__ = "translink_static_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)

    date_fetched: Mapped[date] = mapped_column()
    schedule: Mapped[list[dict]] = mapped_column(JSONB)


class TransLinkRealtimeCacheDB(Base):
    __tablename__ = "translink_realtime_cache"

    id: Mapped[int] = mapped_column(primary_key=True)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    response_bytes: Mapped[bytes] = mapped_column(LargeBinary)
