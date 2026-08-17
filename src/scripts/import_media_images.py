import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

import database
import image_asset.crud
from config import settings

_logger = logging.getLogger(__name__)


async def import_existing_images():
    await database.setup_database()
    image_dir = settings.media_root / "images"
    print(f"Searching {image_dir}")
    if database.sessionmanager is None:
        raise RuntimeError("Database has not been initialized")

    async with database.sessionmanager.session() as session:
        for path in image_dir.rglob("*"):
            if not path.is_file():
                continue

            storage_key = path.relative_to(settings.media_root).as_posix()

            existing = await session.scalar(
                select(image_asset.crud.ImageAssetDB).where(image_asset.crud.ImageAssetDB.storage_key == storage_key)
            )

            if existing is not None:
                continue

            print(f"Adding {storage_key}")
            asset = image_asset.crud.ImageAssetDB(
                storage_key=storage_key,
                original_filename=path.name,
                created_at=datetime.now(UTC),
            )

            session.add(asset)

        await session.commit()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(import_existing_images())
    except Exception:
        _logger.exception("Failed to import existing images")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
