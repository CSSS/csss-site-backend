from datetime import date

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class TransLinkStaticScheduleDB(Base):
    __tablename__ = "translink_static_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)

    date_fetched: Mapped[date] = mapped_column()
    schedule: Mapped[list[dict]] = mapped_column(JSONB)
