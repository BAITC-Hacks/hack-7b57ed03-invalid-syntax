from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class AIConfig:
    mock_mode: bool = settings.mock_mode
    stt_model: Path = settings.stt_model_dir
    diarization_model: Path = settings.diarization_model_dir
    llm_model: Path | None = settings.llm_model_path
    language: str = "auto"


ai_config = AIConfig()
