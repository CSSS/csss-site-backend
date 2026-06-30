from datetime import date

from sqlalchemy import Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from honorary.constants import HONORARY_MEMBER_MAX_LENGTH


class HonoraryMemberDB(Base):
    __tablename__ = "honorary_member"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(HONORARY_MEMBER_MAX_LENGTH), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
