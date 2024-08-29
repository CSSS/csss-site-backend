import logging

import auth.urls
import database
import elections.urls
import officers.urls
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

import tests.urls

logging.basicConfig(level=logging.DEBUG)
database.setup_database()

app = FastAPI(lifespan=database.lifespan, title="CSSS Site Backend")

app.include_router(auth.urls.router)
app.include_router(officers.urls.router)
app.include_router(tests.urls.router)
app.include_router(elections.urls.router)

@app.get("/")
async def read_root():
    return {"message": "Hello! You might be lost, this is actually the sfucsss.org's backend api."}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
        request: Request,
        exception: RequestValidationError
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "detail": exception.errors(),
                "body": exception.body
            }
        )
    )
