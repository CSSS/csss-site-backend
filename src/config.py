from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    environment: str
    db_port: int | None = None

    cookie_secure: bool
    cookie_domain: str | None = None

    frontend_origin: str
    auth_url: str | None = None
    translink_api_key: str | None = None
    kiosk_secret: str | None = None


settings = Settings()  # pyright: ignore[reportCallIssue]
