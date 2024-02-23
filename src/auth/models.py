from sqlalchemy import Column, DateTime, Integer, String, Uuid
#from sqlalchemy.orm import relationship

from database import Base

class UserSession(Base):
    __tablename__ = "user_session"

    # note: a primary key is required for every database table
    id = Column(Integer, primary_key=True)

    issue_time = Column(DateTime, nullable=False)
    session_id = Column(String(512), nullable=False) # the space needed to store 256 bytes in base64
    computing_id = Column(String(32), nullable=False) # technically a max of 8 digits https://www.sfu.ca/computing/about/support/tips/sfu-userid.html
