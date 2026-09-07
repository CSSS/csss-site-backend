import logging
import shutil
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pydantic import WithJsonSchema
from sqlalchemy.exc import IntegrityError
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

import database
import image_asset.crud
from config import settings
from dependencies import perm_admin
from image_asset.constants import ALLOWED_IMAGE_TYPES, IMAGE_ASSET_MAPPING, MAX_ATTEMPTS, MAX_PIXELS, ImageAssetCategory
from image_asset.models import ImageAsset
from image_asset.tables import ImageAssetDB
from utils.shared_models import DetailModel

_logger = logging.getLogger(__name__)


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


def _make_storage_key(category: ImageAssetCategory | None, uuid: UUID, image_format: str) -> str:
    if category is not None:
        cat_path = IMAGE_ASSET_MAPPING.get(category)
        if cat_path is None:
            raise ValueError(f"Image asset mapping missing for category: {category}")
        return f"images/{cat_path}/{uuid}.{image_format}"

    return f"images/{uuid}.{image_format}"


def _create_file(dest: Path, file: UploadFile) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    output = dest.open("xb")

    try:
        with output:
            shutil.copyfileobj(file.file, output)
    except Exception:
        try:
            dest.unlink(missing_ok=True)
        except OSError:
            _logger.exception("Failed to clean up image after failed file write: %s.", dest)
        raise


router = APIRouter(
    prefix="/image",
    tags=["media"],
)


@router.get(
    "",
    description="Get metadata of all image assets, in descending image ID order.",
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
        400: {"description": "Image or category is invalid.", "model": DetailModel},
        403: {"description": "Must be a website admin.", "model": DetailModel},
        413: {"description": f"Maximum resolution of {MAX_PIXELS / 1_000_000} megapixels.", "model": DetailModel},
        415: {"description": "Image format not supported.", "model": DetailModel},
        500: {"description": "Server had an issue saving the image.", "model": DetailModel},
    },
    operation_id="create_image_asset",
    dependencies=[Depends(perm_admin)],
)
async def create_image_asset_from_upload(
    db_session: database.DBSession,
    file: Annotated[UploadFile, WithJsonSchema({"type": "string", "format": "binary"})],
    category: ImageAssetCategory | None = None,
):
    image_format = await validate_upload(file)

    retries = 0
    while retries < MAX_ATTEMPTS:
        committed = False
        file_created = False
        uid = uuid4()
        try:
            storage_key = _make_storage_key(category, uid, image_format)
        except ValueError as e:
            _logger.error(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Image asset mapping missing"
            ) from e
        destination = settings.media_root / storage_key
        await file.seek(0)

        try:
            _create_file(destination, file)
            file_created = True
        except FileExistsError:
            retries += 1
            continue

        try:
            new_img_asset = ImageAssetDB(
                storage_key=storage_key,
                original_filename=file.filename,
            )
            image_asset.crud.create_image_asset(db_session, new_img_asset)
            await db_session.commit()
            committed = True
            await db_session.refresh(new_img_asset)
            return ImageAsset.model_validate(new_img_asset)
        except IntegrityError:
            await db_session.rollback()
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                _logger.exception("Failed to remove image: %s", destination)
            continue
        except Exception as e:
            _logger.exception(e)
            if not committed:
                await db_session.rollback()
                if file_created:
                    try:
                        destination.unlink(missing_ok=True)
                    except OSError:
                        _logger.exception("Failed to remove image: %s", destination)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to make image asset, unhandled exception.",
            ) from e
        finally:
            retries += 1
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to make image asset, exhausted retries."
    )


@router.delete(
    "/{image_id}",
    description="Delete an image asset and its associated file if it's not referenced by anything else.",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Must be a website admin", "model": DetailModel},
        404: {"description": "Image asset doesn't exist", "model": DetailModel},
        409: {"description": "Image asset is still referenced", "model": DetailModel},
        500: {"description": "Deleting image file failed.", "model": DetailModel},
    },
    operation_id="delete_image_asset",
    dependencies=[Depends(perm_admin)],
)
async def delete_image_asset(db_session: database.DBSession, image_id: int):
    db_entry = await image_asset.crud.get_image_asset_by_id(db_session, image_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image can't be found")

    image_path = settings.media_root / db_entry.storage_key

    try:
        await image_asset.crud.delete_image_asset(db_session, db_entry)
        await db_session.commit()
    except IntegrityError as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Image is still referenced by other objects and cannot be deleted.",
        ) from e

    try:
        image_path.unlink(missing_ok=True)
    except OSError as e:
        _logger.error("Failed to delete image file: %s", image_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database entry was deleted, but deleting the image file failed.",
        ) from e

    return Response(status_code=status.HTTP_204_NO_CONTENT)
