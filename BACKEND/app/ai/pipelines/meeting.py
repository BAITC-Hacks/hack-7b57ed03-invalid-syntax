from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from app.ai.contracts import MergedSegment
from app.ai.providers.mock import MockAIProvider
from app.core.config import settings


ProgressCallback = Callable[[str, int], None]


class MeetingProcessingPipeline:
    """Orchestrates providers without coupling the API layer to ML libraries."""

    def __init__(self, progress: ProgressCallback, provider: MockAIProvider | None = None):
        if not settings.mock_mode and provider is None:
            raise RuntimeError("Real AI providers are not configured. Enable MOCK_MODE or register providers.")
        self.progress = progress
        self.provider = provider or MockAIProvider()

    def validate_file(self, source: Path) -> Path:
        self.progress("file_validation", 5)
        if not source.exists() or source.stat().st_size == 0:
            raise ValueError("Uploaded file is empty or unavailable")
        allowed = {".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".mov", ".webm", ".mkv"}
        if source.suffix.lower() not in allowed:
            raise ValueError(f"Unsupported media type: {source.suffix}")
        return source

    def extract_audio(self, source: Path) -> Path:
        self.progress("audio_extraction", 12)
        if source.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"}:
            # Mock mode intentionally keeps the original file. A production adapter
            # will invoke ffmpeg and return a normalized WAV path here.
            return source
        return source

    def preprocess_audio(self, audio: Path) -> Path:
        self.progress("audio_preprocessing", 20)
        return audio

    def transcribe(self, audio: Path):
        self.progress("speech_to_text", 36)
        return self.provider.transcribe(audio)

    def diarize(self, audio: Path):
        self.progress("speaker_diarization", 48)
        return self.provider.diarize(audio)

    def merge_stt_and_diarization(self, speech, turns) -> list[MergedSegment]:
        self.progress("merge_transcript", 56)
        merged: list[MergedSegment] = []
        for segment in speech:
            midpoint = (segment.start + segment.end) / 2
            turn = next((item for item in turns if item.start <= midpoint <= item.end), turns[0])
            merged.append(
                MergedSegment(segment.start, segment.end, turn.speaker, turn.speaker, segment.text)
            )
        return merged

    def identify_speakers(self, transcript: list[MergedSegment]) -> list[MergedSegment]:
        self.progress("speaker_mapping", 64)
        names = {"Speaker_01": "Асхат Ерланович", "Speaker_02": "Гульмира Сериковна"}
        for segment in transcript:
            segment.speaker_name = names.get(segment.speaker_label, segment.speaker_label)
        return transcript

    def extract_tasks(self, transcript, meeting_date):
        self.progress("task_extraction", 75)
        return self.provider.extract(transcript, meeting_date)

    def normalize_deadlines(self, tasks):
        self.progress("deadline_normalization", 81)
        return tasks

    def generate_summary(self, transcript, tasks):
        self.progress("summarization", 88)
        return self.provider.summarize(transcript, tasks)

    def generate_protocol(self) -> None:
        self.progress("protocol_generation", 97)

    def run(self, source: Path, meeting_date):
        source = self.validate_file(source)
        audio = self.extract_audio(source)
        audio = self.preprocess_audio(audio)
        speech = self.transcribe(audio)
        turns = self.diarize(audio)
        transcript = self.merge_stt_and_diarization(speech, turns)
        transcript = self.identify_speakers(transcript)
        tasks = self.extract_tasks(transcript, meeting_date)
        tasks = self.normalize_deadlines(tasks)
        summary = self.generate_summary(transcript, tasks)
        self.progress("saving_results", 93)
        self.generate_protocol()
        return transcript, tasks, summary

