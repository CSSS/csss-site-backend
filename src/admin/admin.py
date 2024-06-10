from fastapi import APIRouter

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)

# TODO: get logs info & enable admins to access it
