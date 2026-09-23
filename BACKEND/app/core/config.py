from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Aqylman Meeting Protocol API"
    api_prefix: str = "/api/v1"
    mock_mode: bool = True
    database_url: str = "sqlite:///./meeting_protocol.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_dir: Path = Path("uploads")
    export_dir: Path = Path("exports")
    max_upload_mb: int = 500
    device: str = "auto"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

