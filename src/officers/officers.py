from fastapi import APIRouter

router = APIRouter(
    prefix="/officers",
    tags=["officers"],
)

@router.get(
    "/current",
    description="Information for all the current officers."
)
async def current_officers():
    return { "officers": "no current officers yet!" }


@router.get(
    "/past",
    description="Information from past exec terms. If year is not included, all years will be returned. If semester is not included, all semesters that year will be returned. If semester is given, but year is not, return all years and all semesters."
)
async def past_officers():
    return { "officers": "none" }


@router.post(
    "/enter_info",
    description="After elections, officer computing ids are input into our system. If you have been elected as a new officer, you may authenticate with SFU CAS, then input your information & the valid token for us."
)
async def enter_info():
    return { }


@router.get(
    "/my_info",
    description="Get info about whether you are still an executive or not / what your position is."
)
async def my_info():
    return { }


@router.post(
    "/new",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Updates the system with a new officer, and enables the user to login to the system to input their information."
)
async def add_new_officer():
    return { }


@router.post(
    "/remove",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Removes the officer from the system entirely. BE CAREFUL WITH THIS OPTION aaaaaaaaaaaaaaaaaa."
)
async def remove_officer():
    return { }


@router.post(
    "/update",
    description="Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Modify the stored info of an existing officer."
)
async def update_officer():
    return { }


