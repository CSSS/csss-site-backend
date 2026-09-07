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
from image_asset.constants import MAX_ATTEMPTS, MAX_PIXELS, ImageAssetCategory
from image_asset.models import ImageAsset

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
    response = await client.get("/api/image")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__upload_image_asset(client: AsyncClient):
    response = await client.post("/api/image")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test__delete_image_asset_requires_authentication(client: AsyncClient):
    response = await client.delete("/api/image/1")
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
    response = await admin_client.get("/api/image")
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
        "/api/image",
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
    ("category", "directory"),
    [
        (ImageAssetCategory.EVENTS, "events"),
        (ImageAssetCategory.EXECS, "execs"),
        (ImageAssetCategory.PHOTOS, "photos"),
    ],
)
async def test__admin_upload_image_to_category(
    db_session: DBSession,
    admin_client: AsyncClient,
    tmp_path: Path,
    category: ImageAssetCategory,
    directory: str,
):
    response = await admin_client.post(
        "/api/image",
        params={"category": category.value},
        files={"file": ("test.png", make_image(), "image/png")},
    )

    assert response.status_code == status.HTTP_201_CREATED

    asset = ImageAsset.model_validate(response.json())

    assert asset.storage_key.startswith(f"images/{directory}/")
    assert asset.storage_key.endswith(".png")
    assert await db_session.get(image_asset.crud.ImageAssetDB, asset.image_id) is not None
    assert (tmp_path / asset.storage_key).is_file()


async def test__admin_upload_invalid_category(
    db_session: DBSession,
    admin_client: AsyncClient,
    tmp_path: Path,
):
    response = await admin_client.post(
        "/api/image",
        params={"category": "invalid"},
        files={"file": ("test.png", make_image(), "image/png")},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert await image_asset.crud.get_all_image_assets(db_session) == []
    assert not any(path.is_file() for path in tmp_path.rglob("*"))


async def test__admin_upload_retries_without_overwriting_existing_file(
    db_session: DBSession,
    admin_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    collision_uuid = UUID("00000000-0000-0000-0000-000000000001")
    successful_uuid = UUID("00000000-0000-0000-0000-000000000002")
    generated_uuids = iter((collision_uuid, successful_uuid))
    monkeypatch.setattr(image_urls, "uuid4", lambda: next(generated_uuids))

    existing_file = tmp_path / f"images/{collision_uuid}.png"
    existing_file.parent.mkdir(parents=True)
    existing_file.write_bytes(b"existing file")

    response = await admin_client.post(
        "/api/image",
        files={"file": ("test.png", make_image(), "image/png")},
    )

    assert response.status_code == status.HTTP_201_CREATED

    asset = ImageAsset.model_validate(response.json())

    assert asset.storage_key == f"images/{successful_uuid}.png"
    assert existing_file.read_bytes() == b"existing file"
    assert (tmp_path / asset.storage_key).is_file()
    assert await db_session.get(image_asset.crud.ImageAssetDB, asset.image_id) is not None


async def test__admin_upload_retries_after_storage_key_conflict(
    db_session: DBSession,
    admin_client: AsyncClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    collision_uuid = UUID("00000000-0000-0000-0000-000000000001")
    successful_uuid = UUID("00000000-0000-0000-0000-000000000002")
    collision_storage_key = f"images/{collision_uuid}.png"

    existing_asset = image_asset.crud.ImageAssetDB(
        storage_key=collision_storage_key,
        original_filename="existing.png",
        created_at=datetime.now(UTC),
    )
    image_asset.crud.create_image_asset(db_session, existing_asset)
    await db_session.commit()

    generated_uuids = iter((collision_uuid, successful_uuid))
    monkeypatch.setattr(image_urls, "uuid4", lambda: next(generated_uuids))

    response = await admin_client.post(
        "/api/image",
        files={"file": ("test.png", make_image(), "image/png")},
    )

    assert response.status_code == status.HTTP_201_CREATED

    asset = ImageAsset.model_validate(response.json())

    assert asset.storage_key == f"images/{successful_uuid}.png"
    assert not (tmp_path / collision_storage_key).exists()
    assert (tmp_path / asset.storage_key).is_file()
    assert len(await image_asset.crud.get_all_image_assets(db_session)) == 2


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
        "/api/image",
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


async def test__admin_exhausted_storage_key_conflicts_are_cleaned_up(
    db_session: DBSession, admin_client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    fixed_uuid = UUID("00000000-0000-0000-0000-000000000001")

    generated_uuids = []

    def generate_fixed_uuid():
        generated_uuids.append(fixed_uuid)
        return fixed_uuid

    monkeypatch.setattr(image_urls, "uuid4", generate_fixed_uuid)

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
        "/api/image",
        files={"file": ("test.png", image_bytes, "image/png")},
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": "Failed to make image asset, exhausted retries."}
    assert len(generated_uuids) == MAX_ATTEMPTS
    saved_file = tmp_path / storage_key

    assert not saved_file.exists()
    assets = await image_asset.crud.get_all_image_assets(db_session)
    assert [asset.storage_key for asset in assets] == [storage_key]


async def test__admin_delete_image_asset(db_session: DBSession, admin_client: AsyncClient, tmp_path: Path):
    upload_response = await admin_client.post(
        "/api/image",
        files={"file": ("test.png", make_image(), "image/png")},
    )
    assert upload_response.status_code == status.HTTP_201_CREATED

    asset = ImageAsset.model_validate(upload_response.json())
    saved_file = tmp_path / asset.storage_key
    assert saved_file.is_file()

    delete_response = await admin_client.delete(f"/api/image/{asset.image_id}")

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    assert delete_response.content == b""
    assert await db_session.get(image_asset.crud.ImageAssetDB, asset.image_id) is None
    assert not saved_file.exists()


async def test__admin_delete_missing_image_asset(admin_client: AsyncClient):
    response = await admin_client.delete("/api/image/0")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Image can't be found"}


async def test__admin_cannot_delete_referenced_image_asset(
    db_session: DBSession,
    admin_client: AsyncClient,
    tmp_path: Path,
):
    upload_response = await admin_client.post(
        "/api/image",
        files={"file": ("referenced.png", make_image(), "image/png")},
    )
    assert upload_response.status_code == status.HTTP_201_CREATED

    asset = ImageAsset.model_validate(upload_response.json())
    saved_file = tmp_path / asset.storage_key

    event_response = await admin_client.post(
        "/api/event",
        json={
            "name": "Event with an image",
            "description": "The image asset must remain available.",
            "start_datetime": "2026-09-05T12:00:00-07:00",
            "end_datetime": "2026-09-05T13:00:00-07:00",
            "status": "scheduled",
            "image_id": asset.image_id,
        },
    )
    assert event_response.status_code == status.HTTP_201_CREATED

    delete_response = await admin_client.delete(f"/api/image/{asset.image_id}")

    assert delete_response.status_code == status.HTTP_409_CONFLICT
    assert delete_response.json() == {"detail": "Image is still referenced by other objects and cannot be deleted."}
    assert await db_session.get(image_asset.crud.ImageAssetDB, asset.image_id) is not None
    assert saved_file.is_file()
