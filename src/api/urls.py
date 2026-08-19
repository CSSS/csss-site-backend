from fastapi import APIRouter

import candidates.urls
import database
import elections.urls
import event.urls
import honorary.urls
import image_asset.urls
import nominees.urls
import officers.urls

router = APIRouter(
    prefix="/api",
)

router.include_router(elections.urls.router)
router.include_router(candidates.urls.router)
router.include_router(nominees.urls.router)
router.include_router(officers.urls.router)
router.include_router(event.urls.router)
router.include_router(honorary.urls.router)
router.include_router(image_asset.urls.router)
