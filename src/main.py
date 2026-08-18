# pyright: reportUnusedImport=false
import contextlib
import logging

import httpx
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import auth.urls
import candidates.urls
import database
import elections.urls
import event.urls
import honorary.urls
import image_asset.urls
import kiosk.urls
import nominees.urls
import officers.urls
import permission.urls
import translink.urls
from config import settings
from dependencies import PERMISSION_DEPENDENCIES

logging.basicConfig(level=logging.DEBUG)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events, see https://fastapi.tiangolo.com/advanced/events/
    """
    await database.setup_database()
    app.state.http_client = httpx.AsyncClient()
    try:
        yield
    finally:
        await app.state.http_client.aclose()
        if database.sessionmanager is not None:
            # Close the DB connection
            await database.sessionmanager.close()


# If on production, disable viewing the docs
if settings.environment == "prod":
    print("Running production environment")
    app = FastAPI(
        lifespan=lifespan,
        title="CSSS Site Backend",
        root_path="/api",
        docs_url=None,  # disables Swagger UI
        redoc_url=None,  # disables ReDoc
        openapi_url=None,  # disables OpenAPI schema
    )
# Enable OpenAPI docs only for local development
else:
    print("Running local environment")
    app = FastAPI(
        lifespan=lifespan,
        title="CSSS Site Backend",
        root_path="/api",
    )
    # Disable authorization checks when on `dev`
    if settings.environment == "dev":
        for dep in PERMISSION_DEPENDENCIES:
            app.dependency_overrides[dep] = lambda: None

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.urls.router)
app.include_router(elections.urls.router)
app.include_router(candidates.urls.router)
app.include_router(nominees.urls.router)
app.include_router(officers.urls.router)
app.include_router(permission.urls.router)
app.include_router(event.urls.router)
app.include_router(honorary.urls.router)
app.include_router(kiosk.urls.router)
app.include_router(image_asset.urls.router)


@app.get("/")
async def read_root():
    return {"message": "Hello! You might be lost, this is actually the sfucsss.org's backend api."}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _: Request,
    exception: RequestValidationError,
):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            {
                "detail": exception.errors(),
                "body": exception.body,
            }
        ),
    )
