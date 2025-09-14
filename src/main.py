import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import auth.urls
import database
import elections.urls
import nominee.urls
import officers.urls
import permission.urls
import registrations.urls
from constants import IS_PROD

logging.basicConfig(level=logging.DEBUG)
database.setup_database()

# Enable OpenAPI docs only for local development
if not IS_PROD:
    print("Running local environment")
    origins = [
        "http://localhost:4200", # default Angular
        "http://localhost:8080", # for existing applications/sites
    ]
    app = FastAPI(
        lifespan=database.lifespan,
        title="CSSS Site Backend",
        root_path="/api",
    )
# if on production, disable viewing the docs
else:
    print("Running production environment")
    origins = [
        "https://sfucsss.org",
        "https://test.sfucsss.org",
        "https://admin.sfucsss.org"
    ]
    app = FastAPI(
        lifespan=database.lifespan,
        title="CSSS Site Backend",
        root_path="/api",
        docs_url=None,  # disables Swagger UI
        redoc_url=None, # disables ReDoc
        openapi_url=None # disables OpenAPI schema
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth.urls.router)
app.include_router(elections.urls.router)
app.include_router(registrations.urls.router)
app.include_router(nominee.urls.router)
app.include_router(officers.urls.router)
app.include_router(permission.urls.router)

@app.get("/")
async def read_root():
    return {"message": "Hello! You might be lost, this is actually the sfucsss.org's backend api."}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request,
    exception: RequestValidationError,
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({
            "detail": exception.errors(),
            "body": exception.body,
        })
    )
