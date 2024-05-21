import pathlib

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

# ----------------------- #

router = APIRouter(prefix="/tests")


@router.get("/{test_name}", description="For use in testing the backend api.")
async def get_test(test_name: str):
    test_path = pathlib.Path(f"../tests/{test_name}")
    test_dir_path = pathlib.Path("../tests/")

    if (test_dir_path in test_path.parents) and test_path.is_file():
        with open(test_path, "r") as file:
            return HTMLResponse(file.read())
    else:
        return HTMLResponse(f"invalid test_name {test_name}")
