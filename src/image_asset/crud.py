from sqlalchemy import select

import database
from config import settings
from image_asset.tables import ImageAssetDB


async def get_all_image_assets(db_session: database.DBSession) -> list[ImageAssetDB]:
    query = select(ImageAssetDB).order_by(ImageAssetDB.image_id.desc())
    return list((await db_session.scalars(query)).all())


def create_image_asset(db_session: database.DBSession, image_asset: ImageAssetDB) -> None:
    db_session.add(image_asset)


async def delete_image_asset(db_session: database.DBSession, image_asset: ImageAssetDB) -> None:
    await db_session.delete(image_asset)
