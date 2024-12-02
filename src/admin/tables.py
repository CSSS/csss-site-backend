from datetime import datetime

from constants import COMPUTING_ID_LEN, SESSION_ID_LEN
from database import Base
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

class AdminLog(Base):
    # The admin log stores any admin-level changes that have been made & by who.
    # It is very much like the discord feature for server moderation.
    __tablename__ = "admin_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)

    computing_id = Column(String(COMPUTING_ID_LEN), nullable=False)

    log_time = Column(DateTime, nullable=False)
    log_description = Column(
        Text, nullable=False
    )

