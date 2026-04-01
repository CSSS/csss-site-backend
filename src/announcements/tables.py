from sqlalchemy import Column, VARCHAR, INTEGER, DATETIME, ForeignKey

from constants import COMPUTING_ID_LEN
from database import Base
from officers import tables

class Announcement(Base):
    __tablename__ = "announcements"

    aid = Column(INTEGER, primary_key=True, autoincrement=True)
    title = Column(VARCHAR(128), nullable=False)
    content = Column(VARCHAR(256), nullable=False)
    date_created = Column(DATETIME(timezone=True), nullable=False)
    computing_id = Column(
        VARCHAR(COMPUTING_ID_LEN),
        ForeignKey("officer_info.computing_id"),
        nullable=False,
    )