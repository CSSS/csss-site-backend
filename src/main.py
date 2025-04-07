import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import auth.urls
import database
import elections.urls
import officers.urls
import permission.urls

logging.basicConfig(level=logging.DEBUG)
database.setup_database()

_login_link = (
    "https://cas.sfu.ca/cas/login?service=" + (
        "http%3A%2F%2Flocalhost%3A8080"
        if os.environ.get("LOCAL") == "true"
        else "https%3A%2F%2Fnew.sfucsss.org"
    ) + "%2Fapi%2Fauth%2Flogin%3Fredirect_path%3D%2Fapi%2Fapi%2Fdocs%2F%26redirect_fragment%3D"
)

app = FastAPI(
    lifespan=database.lifespan,
    title="CSSS Site Backend",
    description=f'To login, please click <a href="{_login_link}">here</a><br><br>To logout from CAS click <a href="https://cas.sfu.ca/cas/logout">here</a>',
    root_path="/api"
)

app.include_router(auth.urls.router)
app.include_router(elections.urls.router)
app.include_router(officers.urls.router)
app.include_router(permission.urls.router)

@app.get("/")
async def read_root():
    return {"message": "Hello! You might be lost, this is actually the sfucsss.org's backend api."}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "detail": exception.errors(),
            "body": exception.body,
        })
    )
