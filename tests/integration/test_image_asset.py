from datetime import UTC, datetime
from http import HTTPStatus
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import UploadFile, status
from httpx import AsyncClient
from PIL import Image
from pydantic import TypeAdapter
from sqlalchemy.exc import IntegrityError

import image_asset.crud
import image_asset.urls as image_urls
from config import settings
from database import DBSession
from image_asset.models import ImageAsset
from image_asset.urls import MAX_PIXELS

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(autouse=True)
def patch_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(settings, "media_root", tmp_path)


def make_image(
    image_format: str = "PNG",
    size: tuple[int, int] = (10, 10),
) -> bytes:
    """
    Creates a file-like image in-memory.

    Args:
        image_format: image format to create e.g., "PNG", "JPEG"
        size: a tuple of width and height in pixels for the image

    Returns:
        An UploadFile object containing the image data.
    """
    buffer = BytesIO()

    image = Image.new("RGB", size)
    image.save(buffer, format=image_format)

    return buffer.getvalue()


# CRUD
async def test__create_image_asset(db_session: DBSession):
    asset = image_asset.crud.ImageAssetDB(
        storage_key="images/test.png", original_filename="test.png", created_at=datetime.now(UTC)
    )

    image_asset.crud.create_image_asset(db_session, asset)

    await db_session.commit()
    await db_session.refresh(asset)

    assert asset.image_id is not None


async def test__get_all_image_assets_is_descending_order(db_session: DBSession):
    for i in range(2):
        asset = image_asset.crud.ImageAssetDB(
            storage_key=f"images/test{i}.png", original_filename=f"test{i}.png", created_at=datetime.now(UTC)
        )
        image_asset.crud.create_image_asset(db_session, asset)

    await db_session.commit()

    res = await image_asset.crud.get_all_image_assets(db_session)

    assert len(res) == 2
    # It returns it in descending image_id order
    assert res[0].storage_key == "images/test1.png"
    assert res[1].storage_key == "images/test0.png"


async def test__duplicate_storage_keys_fails(db_session: DBSession):
    for _ in range(2):
        asset = image_asset.crud.ImageAssetDB(
            storage_key="images/test.png", original_filename="test.png", created_at=datetime.now(UTC)
        )
        image_asset.crud.create_image_asset(db_session, asset)

    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test__delete_image_asset(db_session: DBSession):
    asset = image_asset.crud.ImageAssetDB(
        storage_key="images/test.png", original_filename="test.png", created_at=datetime.now(UTC)
    )
    image_asset.crud.create_image_asset(db_session, asset)

    await db_session.commit()
    await db_session.refresh(asset)

    await image_asset.crud.delete_image_asset(db_session, asset)

    await db_session.commit()

    res = await image_asset.crud.get_all_image_assets(db_session)
    assert len(res) == 0


# Unauthenticated client
async def test__get_all_image_asset_metadata(client: AsyncClient):
    response = await client.get("/image")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__upload_image_asset(client: AsyncClient):
    response = await client.post("/image")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# TODO: Unauthorized client


# Authorized client
async def test__admin_get_all_image_asset_metadata(db_session: DBSession, admin_client: AsyncClient):
    # TODO: Replace this data with a mock factory function.
    for i in range(2):
        asset = image_asset.crud.ImageAssetDB(
            storage_key=f"images/test{i}.png", original_filename=f"test{i}.png", created_at=datetime.now(UTC)
        )
        image_asset.crud.create_image_asset(db_session, asset)
    await db_session.commit()
    response = await admin_client.get("/image")
    assert response.status_code == status.HTTP_200_OK
    data = TypeAdapter(list[ImageAsset]).validate_python(response.json())

    assert len(data) == 2
    assert data[0].storage_key == "images/test1.png"
    assert data[1].storage_key == "images/test0.png"


@pytest.mark.parametrize(
    ("image_format", "filename", "content_type", "extension"),
    [
        ("PNG", "test.png", "image/png", ".png"),
        ("JPEG", "test.jpg", "image/jpeg", ".jpg"),
        ("WEBP", "test.webp", "image/webp", ".webp"),
    ],
    ids=["png", "jpeg", "webp"],
)
async def test__admin_upload_good_image(
    db_session: DBSession,
    admin_client: AsyncClient,
    tmp_path: Path,
    image_format: str,
    filename: str,
    content_type: str,
    extension: str,
):
    image_bytes = make_image(image_format)

    response = await admin_client.post(
        "/image",
        files={
            "file": (
                filename,
                image_bytes,
                content_type,
            )
        },
    )

    assert response.status_code == status.HTTP_201_CREATED

    asset = ImageAsset.model_validate(response.json())

    assert asset.image_id is not None
    assert asset.original_filename == filename
    assert asset.storage_key.startswith("images/")
    assert asset.storage_key.endswith(extension)

    db_asset = await db_session.get(image_asset.crud.ImageAssetDB, asset.image_id)

    assert db_asset is not None
    assert db_asset.storage_key == asset.storage_key
    assert db_asset.original_filename == filename

    saved_file = tmp_path / asset.storage_key

    assert saved_file.exists()
    assert saved_file.is_file()


@pytest.mark.parametrize(
    ("filename", "content", "content_type", "http_status"),
    [
        ("invalid.png", b"invalid image", "image/png", status.HTTP_400_BAD_REQUEST),
        ("test.gif", make_image("GIF"), "image/gif", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
        ("test.png", make_image(size=(int(MAX_PIXELS / 2), 3)), "image/png", status.HTTP_413_CONTENT_TOO_LARGE),
    ],
    ids=["invalid", "unsupported", "oversized"],
)
async def test__admin_upload_invalid_image(
    db_session: DBSession,
    admin_client: AsyncClient,
    tmp_path: Path,
    filename: str,
    content: bytes,
    content_type: str,
    http_status: int,
):

    response = await admin_client.post(
        "/image",
        files={
            "file": (
                filename,
                content,
                content_type,
            )
        },
    )

    # Response is proper
    assert response.status_code == http_status

    # No database entry created
    assets = await image_asset.crud.get_all_image_assets(db_session)
    assert assets == []

    # Physical file exists and has the correct name
    assert not any(path.is_file() for path in tmp_path.rglob("*"))


async def test__admin_failed_db_insert_is_cleaned_up(
    db_session: DBSession, admin_client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fixed_uuid = UUID("00000000-0000-0000-0000-000000000001")

    monkeypatch.setattr(image_urls, "uuid4", lambda: fixed_uuid)

    storage_key = f"images/{fixed_uuid}.png"

    existing_asset = image_asset.crud.ImageAssetDB(
        storage_key=storage_key,
        original_filename="existing.png",
        created_at=datetime.now(UTC),
    )

    image_asset.crud.create_image_asset(db_session, existing_asset)
    await db_session.commit()

    image_bytes = make_image()

    response = await admin_client.post(
        "/image",
        files={"file": ("test.png", image_bytes, "image/png")},
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    saved_file = tmp_path / storage_key

    assert not saved_file.exists()
