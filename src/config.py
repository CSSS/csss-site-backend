from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE)

    environment: str
    db_port: int | None = None

    cookie_secure: bool
    cookie_domain: str | None = None
    allowed_origins: list[str] = []

    auth_url: str | None = None
    auth_redirects: list[str] = []

    translink_api_key: str | None = None
    kiosk_secret: str | None = None

    media_root: Path
    media_base_url: str


settings = Settings()  # pyright: ignore[reportCallIssue]
