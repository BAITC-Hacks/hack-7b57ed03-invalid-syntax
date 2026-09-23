from __future__ import annotations

import os
from pathlib import Path

from app.ai.contracts import SpeakerTurn
from app.ai.errors import DiarizationError, ModelNotFoundError


class LocalDiarizationProvider:
    def __init__(self, model_dir: Path, device: str = "auto"):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        configs = [*model_dir.glob("*.yaml"), *model_dir.glob("*.yml")]
        if not configs:
            raise ModelNotFoundError(f"Локальная модель diarization не найдена: {model_dir}")
        try:
            from pyannote.audio import Pipeline
        except ImportError as exc:
            raise ModelNotFoundError("Не найдена локальная зависимость pyannote.audio.") from exc
        try:
            self.pipeline = Pipeline.from_pretrained(str(configs[0]))
            if device == "cuda":
                import torch
                self.pipeline.to(torch.device("cuda"))
        except Exception as exc:
            raise ModelNotFoundError(f"Не удалось открыть локальную модель diarization: {exc}") from exc

    def diarize(self, audio_path: Path) -> list[SpeakerTurn]:
        try:
            output = self.pipeline(str(audio_path))
            annotation = getattr(output, "speaker_diarization", output)
            labels: dict[str, str] = {}
            turns = []
            for turn, _, raw_label in annotation.itertracks(yield_label=True):
                label = labels.setdefault(raw_label, f"Speaker_{len(labels) + 1:02d}")
                turns.append(SpeakerTurn(float(turn.start), float(turn.end), label))
            if not turns:
                raise DiarizationError("Говорящие не обнаружены.")
            return turns
        except DiarizationError:
            raise
        except Exception as exc:
            raise DiarizationError(f"Не удалось определить говорящих: {exc}") from exc
