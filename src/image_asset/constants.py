from enum import StrEnum
from pathlib import Path


class ImageAssetCategory(StrEnum):
    EVENTS = "events"
    EXECS = "execs"
    PHOTOS = "photos"


IMAGE_ASSET_MAPPING: dict[ImageAssetCategory, Path] = {
    ImageAssetCategory.EVENTS: Path("events"),
    ImageAssetCategory.EXECS: Path("execs"),
    ImageAssetCategory.PHOTOS: Path("photos"),
}

ALLOWED_IMAGE_TYPES = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

MAX_PIXELS = 8_000_000

MAX_ATTEMPTS = 3
