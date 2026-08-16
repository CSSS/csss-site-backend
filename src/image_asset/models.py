from datetime import datetime

from pydantic import BaseModel, Field


class ImageAsset(BaseModel):
    image_id: int = Field(description="The unique identifier for the image asset.")

    original_filename: str = Field(description="The filename used when uploading the image.")

    storage_key: str = Field(description="The path to the image on the storage device.")

    image_url: str = Field(description="The URL to access the image.")

    created_at: datetime = Field(description="The date and time this image was created.")
