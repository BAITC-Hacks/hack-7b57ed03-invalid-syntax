from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol


@dataclass
class SpeechSegment:
    start: float
    end: float
    text: str
    confidence: float = 0.0


@dataclass
class SpeakerTurn:
    start: float
    end: float
    speaker: str


@dataclass
class MergedSegment:
    start: float
    end: float
    speaker_label: str
    speaker_name: str
    text: str
    speaker_role: str | None = None
    speaker_confidence: float = 0.0
    confidence: float = 0.0


@dataclass
class ExtractedTask:
    task: str
    responsible: str
    assigned_by: str
    deadline_raw: str | None
    deadline_normalized: date | None
    original_text: str
    confidence: float


@dataclass
class GeneratedSummary:
    topic: str
    summary_text: str
    key_points: list[str]
    problems: list[str]
    decisions: list[str]
    risks: list[str] | None = None
    metrics: list[str] | None = None


class SpeechToTextProvider(Protocol):
    def transcribe(self, audio_path: Path) -> list[SpeechSegment]: ...


class DiarizationProvider(Protocol):
    def diarize(self, audio_path: Path) -> list[SpeakerTurn]: ...


class TaskExtractionProvider(Protocol):
    def extract(self, transcript: list[MergedSegment], meeting_date: date) -> list[ExtractedTask]: ...


class SummarizationProvider(Protocol):
    def summarize(self, transcript: list[MergedSegment], tasks: list[ExtractedTask]) -> GeneratedSummary: ...
