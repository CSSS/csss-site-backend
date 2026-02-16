from fastapi import APIRouter

from mountain_madness._2026 import CounterResponse, mm_counter

router = APIRouter(
    prefix="/mm",
    tags=["Mountain Madness"],
)


@router.get(
    "/counters",
    description="Get both counters",
    response_description="Get both counters",
    response_model=CounterResponse,
    operation_id="mm_get_counters",
)
async def get_all_counters():
    return CounterResponse(**mm_counter.get_all_counters())


@router.post(
    "/good",
    description="Increment the good counter",
    response_description="Increment the good counter",
    response_model=CounterResponse,
    operation_id="mm_good_increment",
)
async def increment_good():
    mm_counter.increment("good")
    return CounterResponse(**mm_counter.get_all_counters())


@router.post(
    "/evil",
    description="Increment the evil counter",
    response_description="Increment the evil counter",
    response_model=CounterResponse,
    operation_id="mm_evil_increment",
)
async def increment_evil():
    mm_counter.increment("evil")
    return CounterResponse(**mm_counter.get_all_counters())
