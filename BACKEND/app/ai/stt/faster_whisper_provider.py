from __future__ import annotations

import math
from pathlib import Path

from app.ai.contracts import SpeechSegment
from app.ai.errors import ModelNotFoundError, STTError


class FasterWhisperProvider:
    def __init__(self, model_path: Path, device: str = "auto", compute_type: str = "int8"):
        if not model_path.is_dir() or not any(model_path.glob("model.*")):
            raise ModelNotFoundError(f"Локальная Whisper-модель не найдена: {model_path}")
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ModelNotFoundError("Не найдена локальная зависимость faster-whisper.") from exc
        resolved_device = "cuda" if device == "cuda" else "cpu" if device == "cpu" else "auto"
        try:
            self.model = WhisperModel(
                str(model_path), device=resolved_device, compute_type=compute_type, local_files_only=True
            )
        except Exception as exc:
            raise ModelNotFoundError(f"Не удалось открыть локальную Whisper-модель: {exc}") from exc

    def transcribe(self, audio_path: Path) -> list[SpeechSegment]:
        try:
            segments, _info = self.model.transcribe(
                str(audio_path), language=None, beam_size=5, vad_filter=True, condition_on_previous_text=True
            )
            result = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    confidence = max(0.0, min(1.0, math.exp(float(segment.avg_logprob))))
                    result.append(SpeechSegment(float(segment.start), float(segment.end), text, confidence))
            if not result:
                raise STTError("Речь в записи не обнаружена.")
            return result
        except STTError:
            raise
        except Exception as exc:
            raise STTError(f"Не удалось распознать речь: {exc}") from exc
