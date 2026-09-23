from __future__ import annotations

from threading import Lock

from app.ai.diarization.local_provider import LocalDiarizationProvider
from app.ai.providers.local_llm import LocalLLMProvider
from app.ai.stt.faster_whisper_provider import FasterWhisperProvider
from app.core.config import settings


class ModelManager:
    """Process-wide lazy model cache. Models are loaded at most once."""
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._stt = cls._instance._diarization = cls._instance._llm = None
        return cls._instance

    def stt(self):
        if self._stt is None:
            self._stt = FasterWhisperProvider(settings.stt_model_dir, settings.device, settings.stt_compute_type)
        return self._stt

    def diarization(self):
        if self._diarization is None:
            self._diarization = LocalDiarizationProvider(settings.diarization_model_dir, settings.device)
        return self._diarization

    def llm(self):
        if self._llm is None:
            path = settings.llm_model_path
            self._llm = LocalLLMProvider(path, settings.device, settings.llm_context_size) if path else LocalLLMProvider(settings.llm_model_dir / "missing.gguf")
        return self._llm

    def release(self):
        self._stt = self._diarization = self._llm = None


model_manager = ModelManager()
