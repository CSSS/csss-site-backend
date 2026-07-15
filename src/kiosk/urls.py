from fastapi import APIRouter, Depends

import translink.urls
from kiosk.auth import require_kiosk_auth

router = APIRouter(
    prefix="/kiosk",
    tags=["kiosk"],
    dependencies=[Depends(require_kiosk_auth)],
)

router.include_router(translink.urls.router)
