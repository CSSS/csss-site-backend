from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime, Integer, Text

from database import Base


class ImageAssetDB(Base):
    __tablename__ = "image_asset"

    image_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storage_key: Mapped[str] = mapped_column(Text, unique=True)
    original_filename: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
