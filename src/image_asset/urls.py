import logging
import shutil
import warnings
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

import database
import image_asset.crud
from config import settings
from dependencies import perm_admin
from image_asset.models import ImageAsset
from image_asset.tables import ImageAssetDB
from utils.shared_models import DetailModel

_logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}

MAX_PIXELS = 8_000_000


async def validate_upload(file: UploadFile) -> str:
    """
    Ensures the uploaded image is a valid, allowed type and not a decompression bomb.

    Args:
        file: the uploaded file to validate

    Returns:
        the file type of the image

    Raises:
        HTTPException: when the file is not a valid image, too large, or corrupted
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(file.file) as image:
                if image.format not in ALLOWED_IMAGE_TYPES:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail="Unsupported image format.",
                    )

                if image.width * image.height > MAX_PIXELS:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="Image dimensions are too large.",
                    )

                image_format = ALLOWED_IMAGE_TYPES[image.format]
                image.verify()
    except HTTPException:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image.",
        ) from error

    # Need to reset file pointer after reading
    await file.seek(0)

    return image_format


router = APIRouter(
    prefix="/image",
    tags=["image", "media"],
)


@router.get(
    "",
    description="Get metadata of all image assets",
    response_model=list[ImageAsset],
    responses={403: {"description": "must be a website admin", "model": DetailModel}},
    operation_id="get_all_image_assets",
    dependencies=[Depends(perm_admin)],
)
async def get_all_image_assets(db_session: database.DBSession):
    return await image_asset.crud.get_all_image_assets(db_session)


@router.post(
    "",
    description="Create a new image asset.",
    response_model=ImageAsset,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Image is invalid", "model": DetailModel},
        403: {"description": "Must be a website admin", "model": DetailModel},
        413: {"description": f"Maximum resolution of {MAX_PIXELS / 1_000_000} megapixels", "model": DetailModel},
        415: {"description": "Image format not supported.", "model": DetailModel},
        500: {"description": "Saving image failed", "model": DetailModel},
    },
    operation_id="create_image_asset",
    dependencies=[Depends(perm_admin)],
)
async def create_image_asset_from_upload(file: UploadFile, db_session: database.DBSession):
    image_format = await validate_upload(file)

    storage_key = f"images/{uuid4()}.{image_format}"
    destination = settings.media_root / storage_key

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)

        with destination.open("wb") as output:
            shutil.copyfileobj(file.file, output)
    except OSError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image to storage.",
        ) from error

    new_img_asset = ImageAssetDB(
        storage_key=storage_key,
        original_filename=file.filename,
    )

    try:
        image_asset.crud.create_image_asset(db_session, new_img_asset)
        await db_session.commit()
        await db_session.refresh(new_img_asset)
    except Exception as e:
        await db_session.rollback()

        try:
            destination.unlink(missing_ok=True)
        except OSError:
            # This logs to ensure we know there's now an orphaned file being stored.
            _logger.info("Failed to clean up image after failed DB insertion.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clean up image after failed write.",
        ) from e

    return new_img_asset
