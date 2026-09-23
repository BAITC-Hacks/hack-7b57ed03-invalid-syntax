from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import re

from pydantic import BaseModel, Field, ValidationError

from app.ai.contracts import ExtractedTask, GeneratedSummary, MergedSegment
from app.ai.deadline_parser.parser import parse_deadline
from app.ai.errors import LLMError, ModelNotFoundError, TaskExtractionError


class PersonItem(BaseModel):
    speaker_label: str
    display_name: str | None = None
    role: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class PeopleOutput(BaseModel):
    participants: list[PersonItem]


class TaskItem(BaseModel):
    task: str
    responsible: str = "Не определён"
    assigned_by: str = "Не определён"
    deadline_raw: str | None = None
    original_text: str
    confidence: float = Field(default=0.5, ge=0, le=1)


class TasksOutput(BaseModel):
    tasks: list[TaskItem]


class SummaryOutput(BaseModel):
    topic: str
    summary_text: str
    key_points: list[str] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)


class LocalLLMProvider:
    def __init__(self, model_path: Path, device: str = "auto", context_size: int = 8192):
        if not model_path.is_file() or model_path.suffix.casefold() != ".gguf":
            raise ModelNotFoundError(f"Локальная GGUF-модель не найдена: {model_path}")
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise ModelNotFoundError("Не найдена локальная зависимость llama-cpp-python.") from exc
        try:
            self.model = Llama(
                model_path=str(model_path), n_ctx=context_size,
                n_gpu_layers=-1 if device in {"auto", "cuda"} else 0, verbose=False,
            )
        except Exception as exc:
            raise ModelNotFoundError(f"Не удалось открыть локальную GGUF-модель: {exc}") from exc

    def _json(self, instruction: str, payload: str) -> dict:
        try:
            response = self.model.create_chat_completion(
                messages=[
                    {"role": "system", "content": instruction + " Верни только валидный JSON без markdown."},
                    {"role": "user", "content": payload},
                ], temperature=0.1, max_tokens=2048,
                response_format={"type": "json_object"},
            )
            content = response["choices"][0]["message"]["content"] or ""
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
                raise
        except Exception as exc:
            raise LLMError(f"Локальная модель вернула некорректный ответ: {exc}") from exc

    @staticmethod
    def _transcript(transcript: list[MergedSegment]) -> str:
        return "\n".join(
            f"[{s.start:.1f}-{s.end:.1f}] {s.speaker_label}: {s.text}" for s in transcript
        )

    def map_speakers(self, transcript: list[MergedSegment]) -> list[MergedSegment]:
        data = self._json(
            "Определи имена и должности говорящих только по явным обращениям и представлениям. "
            "Не выдумывай. Неизвестные значения верни null. Схема: "
            '{"participants":[{"speaker_label":"Speaker_01","display_name":null,"role":null,"confidence":0.0}]}.',
            self._transcript(transcript),
        )
        try:
            people = PeopleOutput.model_validate(data).participants
        except ValidationError as exc:
            raise LLMError(f"Некорректная схема участников: {exc}") from exc
        mapped = {p.speaker_label: p for p in people}
        labels = {s.speaker_label for s in transcript}
        ordinal = {label: index + 1 for index, label in enumerate(sorted(labels))}
        for segment in transcript:
            person = mapped.get(segment.speaker_label)
            segment.speaker_name = person.display_name if person and person.display_name else f"Speaker {ordinal[segment.speaker_label]}"
            segment.speaker_role = person.role if person else None
            segment.speaker_confidence = person.confidence if person else 0.0
        return transcript

    def extract(self, transcript: list[MergedSegment], meeting_date: date) -> list[ExtractedTask]:
        try:
            data = self._json(
                "Извлеки все поручения из полного контекста совещания. Учитывай адресата предыдущих реплик, "
                "несколько действий и подразделения. Не выдумывай имена и сроки. Схема: "
                '{"tasks":[{"task":"...","responsible":"...","assigned_by":"...",'
                '"deadline_raw":null,"original_text":"...","confidence":0.0}]}.',
                f"Дата совещания: {meeting_date.isoformat()}\n" + self._transcript(transcript),
            )
        except LLMError as exc:
            raise TaskExtractionError(str(exc).split(": ", 1)[-1]) from exc
        try:
            items = TasksOutput.model_validate(data).tasks
        except ValidationError as exc:
            raise TaskExtractionError(f"Некорректная схема поручений: {exc}") from exc
        return [ExtractedTask(
            task=item.task.strip(), responsible=item.responsible.strip(), assigned_by=item.assigned_by.strip(),
            deadline_raw=item.deadline_raw, deadline_normalized=parse_deadline(item.deadline_raw, meeting_date),
            original_text=item.original_text.strip(), confidence=item.confidence,
        ) for item in items if item.task.strip()]

    def summarize(self, transcript: list[MergedSegment], tasks: list[ExtractedTask]) -> GeneratedSummary:
        data = self._json(
            "Создай точное деловое резюме совещания на языке разговора. Не добавляй факты. Схема: "
            '{"topic":"...","summary_text":"...","key_points":[],"problems":[],"decisions":[],"risks":[],"metrics":[]}.',
            self._transcript(transcript),
        )
        try:
            item = SummaryOutput.model_validate(data)
        except ValidationError as exc:
            raise LLMError(f"Некорректная схема summary: {exc}") from exc
        return GeneratedSummary(**item.model_dump())
