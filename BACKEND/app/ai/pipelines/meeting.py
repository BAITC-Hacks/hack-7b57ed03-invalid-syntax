from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import tempfile

from app.ai.audio.audio_processor import AudioProcessor
from app.ai.contracts import GeneratedSummary, MergedSegment
from app.ai.errors import AIError
from app.ai.model_manager import model_manager
from app.ai.providers.mock import MockAIProvider
from app.ai.providers.openai_provider import OpenAIMeetingProvider
from app.ai.speaker_mapping.mapper import contextual_speaker_mapping
from app.core.config import settings

ProgressCallback = Callable[[str, int], None]


@dataclass
class PipelineResult:
    transcript: list[MergedSegment]
    tasks: list
    summary: GeneratedSummary | None
    warnings: list[str]


class MeetingProcessingPipeline:
    def __init__(self, progress: ProgressCallback, provider=None):
        self.progress = progress
        self.mode = settings.ai_mode
        self.provider = provider
        if self.provider is None and self.mode == "demo":
            self.provider = MockAIProvider()
        self.audio_processor = AudioProcessor()

    def validate_file(self, source: Path) -> Path:
        self.progress("file_validation", 5)
        allowed = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}
        if not source.is_file() or source.stat().st_size == 0:
            raise AIError("FILE_INVALID: Файл пуст или недоступен.")
        if source.suffix.casefold() not in allowed:
            raise AIError(f"FILE_INVALID: Неподдерживаемый формат {source.suffix}.")
        if source.stat().st_size > settings.max_upload_mb * 1024 * 1024:
            raise AIError(f"FILE_TOO_LARGE: Максимальный размер файла — {settings.max_upload_mb} МБ.")
        if self.mode == "local":
            self.audio_processor.validate_media(source)
        return source

    def prepare_audio(self, source: Path, workdir: Path) -> Path:
        self.progress("audio_extraction", 10)
        if self.mode != "local":
            return source
        self.progress("audio_preprocessing", 20)
        return self.audio_processor.normalize_audio(source, workdir / "normalized.wav")

    @staticmethod
    def merge_stt_and_diarization(speech, turns) -> list[MergedSegment]:
        merged = []
        for segment in speech:
            overlaps: dict[str, float] = {}
            for turn in turns:
                overlap = max(0.0, min(segment.end, turn.end) - max(segment.start, turn.start))
                if overlap:
                    overlaps[turn.speaker] = overlaps.get(turn.speaker, 0.0) + overlap
            label = max(overlaps, key=overlaps.get) if overlaps else "Speaker_01"
            merged.append(
                MergedSegment(
                    start=segment.start,
                    end=segment.end,
                    speaker_label=label,
                    speaker_name=label,
                    text=segment.text,
                    confidence=segment.confidence,
                )
            )
        return merged

    def _run_demo(self, source: Path, meeting_date: date) -> PipelineResult:
        provider = self.provider or MockAIProvider()
        self.progress("speech_to_text", 25)
        speech = provider.transcribe(source)
        self.progress("speaker_diarization", 55)
        turns = provider.diarize(source)
        self.progress("merge_transcript", 70)
        transcript = contextual_speaker_mapping(self.merge_stt_and_diarization(speech, turns))
        self.progress("task_extraction", 82)
        tasks = provider.extract(transcript, meeting_date)
        self.progress("summarization", 94)
        summary = provider.summarize(transcript, tasks)
        self.progress("saving_results", 98)
        return PipelineResult(transcript, tasks, summary, [])

    def _run_openai(self, source: Path, meeting_date: date) -> PipelineResult:
        provider = self.provider or OpenAIMeetingProvider()
        self.progress("speech_to_text", 20)
        transcript = provider.transcribe_and_diarize(source)
        self.progress("speaker_diarization", 65)
        self.progress("task_extraction", 78)
        tasks, summary = provider.analyze(transcript, meeting_date)
        self.progress("summarization", 94)
        self.progress("saving_results", 98)
        return PipelineResult(transcript, tasks, summary, [])

    def _run_local(self, source: Path, meeting_date: date) -> PipelineResult:
        warnings: list[str] = []
        with tempfile.TemporaryDirectory(prefix="alem-") as temp:
            audio = self.prepare_audio(source, Path(temp))
            self.progress("speech_to_text", 25)
            speech = model_manager.stt().transcribe(audio)
            self.progress("speech_to_text", 50)
            self.progress("speaker_diarization", 55)
            try:
                turns = model_manager.diarization().diarize(audio)
            except AIError as exc:
                turns = []
                warnings.append(str(exc) + " Транскрипт сохранён без надёжного разделения спикеров.")
            self.progress("merge_transcript", 70)
            transcript = self.merge_stt_and_diarization(speech, turns)
            self.progress("speaker_mapping", 75)
            try:
                llm = model_manager.llm()
                transcript = llm.map_speakers(transcript)
            except AIError as exc:
                llm = None
                transcript = contextual_speaker_mapping(transcript)
                warnings.append(str(exc) + " Имена можно исправить вручную.")
            self.progress("task_extraction", 82)
            tasks = []
            summary = None
            if llm:
                try:
                    tasks = llm.extract(transcript, meeting_date)
                except AIError as exc:
                    warnings.append(str(exc) + " Транскрипт сохранён.")
                self.progress("summarization", 94)
                try:
                    summary = llm.summarize(transcript, tasks)
                except AIError as exc:
                    warnings.append(str(exc) + " Транскрипт сохранён.")
            self.progress("saving_results", 98)
            return PipelineResult(transcript, tasks, summary, warnings)

    def run(self, source: Path, meeting_date: date) -> PipelineResult:
        source = self.validate_file(source)
        if self.mode == "openai":
            return self._run_openai(source, meeting_date)
        if self.mode == "local":
            return self._run_local(source, meeting_date)
        return self._run_demo(source, meeting_date)
