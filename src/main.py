# pyright: reportUnusedImport=false
import contextlib
import logging

import httpx
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import api.urls
import auth.urls
import database
import kiosk.urls
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
        docs_url=None,  # disables Swagger UI
        redoc_url=None,  # disables ReDoc
    )
# Enable OpenAPI docs only for local development
else:
    print("Running local environment")
    app = FastAPI(
        lifespan=lifespan,
        title="CSSS Site Backend",
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
app.include_router(api.urls.router)
app.include_router(kiosk.urls.router)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


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
