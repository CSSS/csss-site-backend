from fastapi import APIRouter

router = APIRouter(
    prefix="/permission",
    tags=["permission"],
)

# TODO: add an endpoint for viewing permissions that exist & what levels they can have & what levels each person has
