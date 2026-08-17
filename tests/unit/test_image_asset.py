from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile, status
from PIL import Image

from image_asset.urls import ALLOWED_IMAGE_TYPES, MAX_PIXELS, validate_upload

pytestmark = pytest.mark.unit


def make_image(
    image_format: str = "PNG",
    size: tuple[int, int] = (10, 10),
) -> UploadFile:
    """
    Creates a temporary PNG in-memory.

    Args:
        image_format: image format to create e.g., "PNG", "JPEG"
        size: a tuple of width and height in pixels for the image

    Returns:
        An UploadFile object containing the image data.
    """
    buffer = BytesIO()

    image = Image.new("RGB", size)
    image.save(buffer, format=image_format)

    buffer.seek(0)

    return UploadFile(
        filename=f"test.{image_format.lower()}",
        file=buffer,
    )


def make_corrupted_image(
    image_format: str = "PNG",
    size: tuple[int, int] = (10, 10),
) -> UploadFile:
    """
    Creates a temporary PNG in-memory and then truncates some bytes.

    Args:
        image_format: image format to create e.g., "PNG", "JPEG"
        size: a tuple of width and height in pixels for the image

    Returns:
        An UploadFile object containing the image data.
    """
    buffer = BytesIO()

    image = Image.new("RGB", size)
    image.save(buffer, format=image_format)

    data = buffer.getvalue()

    corrupted_data = data[:-10]  # Remove the last 10 bytes to corrupt the image

    return UploadFile(
        filename=f"test.{image_format.lower()}",
        file=BytesIO(corrupted_data),
    )


async def test__supported_image_types_are_valid():
    for pil_type, img_type in ALLOWED_IMAGE_TYPES.items():
        file = make_image(pil_type)
        result = await validate_upload(file)

        assert result == img_type


async def test__maximum_image_resolution_accepted():
    file = make_image(size=(int(MAX_PIXELS / 2), 2))
    result = await validate_upload(file)

    assert result == "png"


async def test__invalid_image():
    file = make_image("PDF")

    with pytest.raises(HTTPException) as ex:
        await validate_upload(file)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST


async def test__unsupported_image():
    file = make_image("GIF")

    with pytest.raises(HTTPException) as ex:
        await validate_upload(file)

    assert ex.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE


async def test__image_resolution_high():
    file = make_image("PNG", size=(int(MAX_PIXELS / 2) + 1, 2))

    with pytest.raises(HTTPException) as ex:
        await validate_upload(file)

    assert ex.value.status_code == status.HTTP_413_CONTENT_TOO_LARGE


async def test__corrupted_image():
    file = make_corrupted_image()

    with pytest.raises(HTTPException) as ex:
        await validate_upload(file)

    assert ex.value.status_code == status.HTTP_400_BAD_REQUEST
