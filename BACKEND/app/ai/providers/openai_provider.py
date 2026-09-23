from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.ai.contracts import ExtractedTask, GeneratedSummary, MergedSegment
from app.ai.deadline_parser.parser import parse_deadline
from app.ai.errors import LLMError, OpenAIAPIError, STTError
from app.core.config import settings


class OpenAITask(BaseModel):
    task: str
    responsible: str | None
    assigned_by: str | None
    deadline_raw: str | None
    deadline_normalized: str | None
    original_text: str
    confidence: float = Field(ge=0, le=1)


class OpenAIAnalysis(BaseModel):
    topic: str
    summary: str
    key_points: list[str]
    decisions: list[str]
    problems: list[str]
    tasks: list[OpenAITask]


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _speaker_name(label: str) -> str:
    clean = label.strip()
    lowered = clean.casefold()
    if lowered.startswith("speaker"):
        suffix = clean[len("speaker"):].strip(" _-")
        return f"Спикер {suffix}" if suffix else "Спикер"
    if lowered.startswith("спикер"):
        return clean
    return f"Спикер {clean}"


def _friendly_api_error(exc: Exception) -> str:
    kind = type(exc).__name__
    if kind == "AuthenticationError":
        return "OpenAI API key отклонён. Проверьте OPENAI_API_KEY."
    if kind == "RateLimitError":
        return "OpenAI API временно ограничил запросы или на аккаунте закончилась квота."
    if kind in {"APIConnectionError", "APITimeoutError"}:
        return "Не удалось подключиться к OpenAI API. Проверьте интернет-соединение."
    status = getattr(exc, "status_code", None)
    if status:
        return f"OpenAI API вернул HTTP {status}."
    return f"OpenAI API недоступен: {exc}"


class OpenAIMeetingProvider:
    """Official OpenAI SDK adapter for diarized transcription and structured analysis."""

    def __init__(self, client: Any = None):
        if not settings.openai_api_key and client is None:
            raise OpenAIAPIError("OPENAI_API_KEY не настроен.")
        if client is not None:
            self.client = client
            return
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OpenAIAPIError("Пакет openai не установлен. Выполните pip install -r requirements.txt.") from exc
        self.client = OpenAI(api_key=settings.openai_api_key)

    def transcribe_and_diarize(self, audio_path: Path) -> list[MergedSegment]:
        try:
            with audio_path.open("rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=settings.openai_transcription_model,
                    file=audio_file,
                    response_format="diarized_json",
                    chunking_strategy="auto",
                )
        except Exception as exc:
            raise STTError(_friendly_api_error(exc)) from exc

        segments = _value(response, "segments", []) or []
        transcript: list[MergedSegment] = []
        for segment in segments:
            text = str(_value(segment, "text", "")).strip()
            if not text:
                continue
            label = str(_value(segment, "speaker", "Unknown")).strip() or "Unknown"
            transcript.append(
                MergedSegment(
                    start=float(_value(segment, "start", 0.0) or 0.0),
                    end=float(_value(segment, "end", 0.0) or 0.0),
                    speaker_label=label,
                    speaker_name=_speaker_name(label),
                    text=text,
                    confidence=0.0,
                )
            )
        if not transcript:
            raise STTError("OpenAI не вернул сегменты распознанной речи.")
        return transcript

    @staticmethod
    def _transcript_text(transcript: list[MergedSegment]) -> str:
        return "\n".join(
            f"[{item.start:.2f}-{item.end:.2f}] {item.speaker_name} "
            f"(label={item.speaker_label}): {item.text}"
            for item in transcript
        )

    def analyze(
        self, transcript: list[MergedSegment], meeting_date: date
    ) -> tuple[list[ExtractedTask], GeneratedSummary]:
        instructions = (
            "Ты составляешь точный протокол делового совещания на русском, казахском или смешанном языке. "
            "Сохраняй язык и факты исходного разговора. Не придумывай поручения, решения, проблемы, имена "
            "или сроки. Если элементов нет, возвращай пустой массив. Поручением считается только явная просьба, "
            "назначение или обязательство выполнить действие. Для неизвестного ответственного или автора верни null. "
            "Если ответственный или автор является одним из размеченных спикеров, используй его отображаемую метку "
            "из транскрипта (например, «Спикер A»), чтобы пользователь затем мог заменить её настоящим именем. "
            "deadline_normalized возвращай как YYYY-MM-DD относительно даты совещания либо null. "
            "original_text должен быть точной исходной фразой. Ответ должен строго соответствовать схеме."
        )
        payload = (
            f"Дата совещания: {meeting_date.isoformat()}\n"
            "Ниже дан полный diarized-транскрипт. Метки спикеров нельзя менять или придумывать.\n\n"
            + self._transcript_text(transcript)
        )
        try:
            response = self.client.responses.parse(
                model=settings.openai_text_model,
                input=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": payload},
                ],
                text_format=OpenAIAnalysis,
            )
            parsed = response.output_parsed
            if parsed is None:
                raise ValueError("модель не вернула структурированный результат")
        except Exception as exc:
            raise LLMError(_friendly_api_error(exc)) from exc

        tasks: list[ExtractedTask] = []
        for item in parsed.tasks:
            task_text = item.task.strip()
            if not task_text:
                continue
            normalized = None
            if item.deadline_normalized:
                try:
                    normalized = date.fromisoformat(item.deadline_normalized)
                except ValueError:
                    normalized = None
            if normalized is None:
                normalized = parse_deadline(item.deadline_raw, meeting_date)
            tasks.append(
                ExtractedTask(
                    task=task_text,
                    responsible=(item.responsible or "Не определён").strip(),
                    assigned_by=(item.assigned_by or "Не определён").strip(),
                    deadline_raw=item.deadline_raw,
                    deadline_normalized=normalized,
                    original_text=item.original_text.strip(),
                    confidence=item.confidence,
                )
            )
        summary = GeneratedSummary(
            topic=parsed.topic.strip() or "Тема не определена",
            summary_text=parsed.summary.strip(),
            key_points=[value.strip() for value in parsed.key_points if value.strip()],
            decisions=[value.strip() for value in parsed.decisions if value.strip()],
            problems=[value.strip() for value in parsed.problems if value.strip()],
        )
        return tasks, summary
