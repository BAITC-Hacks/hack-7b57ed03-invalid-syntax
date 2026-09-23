from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Aqylman Meeting Protocol API"
    api_prefix: str = "/api/v1"
    mock_mode: bool = False
    ai_provider: str = "auto"
    openai_api_key: str | None = None
    openai_transcription_model: str = "gpt-4o-transcribe-diarize"
    openai_text_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./meeting_protocol.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    upload_dir: Path = Path("uploads")
    export_dir: Path = Path("exports")
    max_upload_mb: int = 25
    device: str = "auto"
    stt_model_dir: Path = Path("models/whisper")
    diarization_model_dir: Path = Path("models/diarization")
    llm_model_dir: Path = Path("models/llm")
    ffmpeg_path: str | None = None
    stt_compute_type: str = "int8"
    llm_context_size: int = 8192

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ai_mode(self) -> str:
        """Resolve the runtime provider without making startup depend on credentials."""
        provider = self.ai_provider.strip().casefold()
        if self.mock_mode or provider == "demo":
            return "demo"
        if provider == "local":
            return "local"
        if self.openai_api_key and provider in {"auto", "openai"}:
            return "openai"
        return "demo"

    @staticmethod
    def has_files(folder: Path, patterns: tuple[str, ...]) -> bool:
        return folder.is_dir() and any(any(folder.rglob(pattern)) for pattern in patterns)

    @property
    def stt_model_available(self) -> bool:
        return (self.stt_model_dir / "model.bin").is_file() and (self.stt_model_dir / "config.json").is_file()

    @property
    def diarization_model_available(self) -> bool:
        has_config = self.has_files(self.diarization_model_dir, ("*.yaml", "*.yml"))
        has_weights = self.has_files(self.diarization_model_dir, ("*.bin", "*.safetensors", "*.ckpt", "*.pt"))
        return has_config and has_weights

    @property
    def llm_model_path(self) -> Path | None:
        return next(self.llm_model_dir.glob("*.gguf"), None) if self.llm_model_dir.is_dir() else None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

