from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class AIConfig:
    mock_mode: bool = settings.mock_mode
    stt_model: str = "faster-whisper-small"
    diarization_model: str = "pyannote/speaker-diarization"
    language: str = "auto"


ai_config = AIConfig()

