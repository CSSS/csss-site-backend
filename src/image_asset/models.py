from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from config import settings


class ImageAsset(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    image_id: int = Field(
        description="The unique identifier for the image asset.",
    )

    original_filename: str = Field(
        description="The filename used when uploading the image.",
    )

    storage_key: str = Field(
        description="The path to the image on the storage device.",
    )

    created_at: datetime = Field(
        description="The date, time, and timezone this image was created.",
    )

    @computed_field(description="Public URL to access the image asset.")
    @property
    def image_url(self) -> str:
        return f"{settings.media_base_url.rstrip('/')}/{self.storage_key}"
