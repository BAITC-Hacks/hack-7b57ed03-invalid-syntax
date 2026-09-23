from datetime import date, timedelta
from pathlib import Path

from app.ai.contracts import (
    ExtractedTask,
    GeneratedSummary,
    MergedSegment,
    SpeakerTurn,
    SpeechSegment,
)


class MockAIProvider:
    """Deterministic provider that exercises the complete application contract."""

    def transcribe(self, audio_path: Path) -> list[SpeechSegment]:
        return [
            SpeechSegment(0.0, 5.8, "Коллеги, обсудим подготовку презентации по пилотному проекту.", 0.95),
            SpeechSegment(6.1, 13.4, "Ануар Темиргалиев, вам слово. Подготовьте презентацию до пятницы."),
            SpeechSegment(13.8, 22.0, "Принял. Соберу показатели по одиннадцати площадкам и текущим рискам."),
            SpeechSegment(22.4, 31.6, "Добавьте результаты проверки двух датчиков и направьте финальную версию мне."),
            SpeechSegment(32.0, 40.2, "Хорошо, отчёт и презентацию отправлю до конца недели."),
        ]

    def diarize(self, audio_path: Path) -> list[SpeakerTurn]:
        return [
            SpeakerTurn(0.0, 13.4, "Speaker_01"),
            SpeakerTurn(13.8, 22.0, "Speaker_02"),
            SpeakerTurn(22.4, 31.6, "Speaker_01"),
            SpeakerTurn(32.0, 40.2, "Speaker_02"),
        ]

    def extract(self, transcript: list[MergedSegment], meeting_date: date) -> list[ExtractedTask]:
        days_until_friday = (4 - meeting_date.weekday()) % 7 or 7
        return [
            ExtractedTask(
                task="Подготовить презентацию по пилотному проекту",
                responsible="Ануар Темиргалиев",
                assigned_by="Speaker 1",
                deadline_raw="до пятницы",
                deadline_normalized=meeting_date + timedelta(days=days_until_friday),
                original_text="Ануар Темиргалиев, вам слово. Подготовьте презентацию до пятницы.",
                confidence=0.94,
            ),
            ExtractedTask(
                task="Добавить результаты проверки датчиков и направить финальную версию",
                responsible="Ануар Темиргалиев",
                assigned_by="Speaker 1",
                deadline_raw="до конца недели",
                deadline_normalized=meeting_date + timedelta(days=days_until_friday),
                original_text="Добавьте результаты проверки двух датчиков и направьте финальную версию мне.",
                confidence=0.86,
            ),
        ]

    def summarize(self, transcript: list[MergedSegment], tasks: list[ExtractedTask]) -> GeneratedSummary:
        return GeneratedSummary(
            topic="Подготовка презентации по пилотному проекту",
            summary_text="Участники согласовали содержание презентации, перечень показателей и срок подготовки финальной версии.",
            key_points=[
                "Пилот охватывает 11 площадок.",
                "В презентацию войдут результаты по 11 площадкам.",
                "Необходимо отразить результаты проверки двух датчиков.",
            ],
            problems=["Требуется подтвердить результаты проверки двух датчиков."],
            decisions=["Подготовить и направить финальную презентацию до конца недели."],
        )
