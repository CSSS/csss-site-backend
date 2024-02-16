from fastapi import APIRouter

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

@router.get("/current")
async def current_officers():
    return { "message": "no current officers yet!" }


