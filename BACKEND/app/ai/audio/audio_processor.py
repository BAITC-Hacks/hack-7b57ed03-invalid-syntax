from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

from app.ai.errors import FFmpegNotFoundError, AIError
from app.core.config import settings


class AudioProcessor:
    def __init__(self):
        configured = Path(settings.ffmpeg_path) if settings.ffmpeg_path else None
        self.ffmpeg = str(configured) if configured and configured.is_file() else shutil.which("ffmpeg")
        self.ffprobe = shutil.which("ffprobe")

    @property
    def available(self) -> bool:
        return bool(self.ffmpeg)

    def validate_media(self, source: Path) -> None:
        if not source.is_file() or source.stat().st_size == 0:
            raise AIError("FILE_INVALID: Файл пуст или недоступен.")
        if self.ffprobe:
            result = subprocess.run(
                [self.ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(source)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode or not result.stdout.strip():
                raise AIError("FILE_INVALID: Файл не является поддерживаемым аудио или видео.")

    def normalize_audio(self, source: Path, destination: Path) -> Path:
        if not self.ffmpeg:
            raise FFmpegNotFoundError("FFmpeg не найден. Установите локальный FFmpeg.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destination)],
            capture_output=True, text=True, timeout=3600,
        )
        if result.returncode or not destination.is_file() or destination.stat().st_size <= 44:
            raise AIError("AUDIO_PREPROCESSING_FAILED: Не удалось подготовить аудио. " + result.stderr[-300:])
        return destination

    extract_audio = normalize_audio
