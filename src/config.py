from ctypes import Union
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE)

    # Application settings
    environment: Literal["dev"] | Literal["prod"] | Literal["test"]
    db_port: int | None = None
    app_url: str

    # CORS and cookie settings
    cookie_secure: bool
    cookie_domain: str | None = None
    allowed_origins: list[str] = []

    # Authentication settings
    allowed_return_origins: list[str] = []

    # API keys and secrets
    translink_api_key: str | None = None
    kiosk_secret: str | None = None

    # Media settings
    media_root: Path
    media_base_url: str


settings = Settings()  # pyright: ignore[reportCallIssue]
