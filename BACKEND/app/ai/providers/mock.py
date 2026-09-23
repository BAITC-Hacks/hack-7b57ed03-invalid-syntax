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
            SpeechSegment(0.0, 5.8, "Коллеги, обсудим готовность пилота на одиннадцати площадках."),
            SpeechSegment(6.1, 13.4, "Гульмира Сериковна, вам слово по текущим рискам."),
            SpeechSegment(13.8, 22.0, "Два датчика требуют повторной проверки, поставщик уже уведомлён."),
            SpeechSegment(22.4, 31.6, "Нурлан Сагатович, проведите аудит датчиков до пятницы."),
            SpeechSegment(32.0, 40.2, "Отчёт направьте мне, после этого запускаем пилот."),
        ]

    def diarize(self, audio_path: Path) -> list[SpeakerTurn]:
        return [
            SpeakerTurn(0.0, 13.4, "Speaker_01"),
            SpeakerTurn(13.8, 22.0, "Speaker_02"),
            SpeakerTurn(22.4, 40.2, "Speaker_01"),
        ]

    def extract(self, transcript: list[MergedSegment], meeting_date: date) -> list[ExtractedTask]:
        days_until_friday = (4 - meeting_date.weekday()) % 7 or 7
        return [
            ExtractedTask(
                task="Провести аудит датчиков на 11 площадках",
                responsible="Нурлан Сагатович",
                assigned_by="Асхат Ерланович",
                deadline_raw="до пятницы",
                deadline_normalized=meeting_date + timedelta(days=days_until_friday),
                original_text="Нурлан Сагатович, проведите аудит датчиков до пятницы.",
                confidence=0.94,
            ),
            ExtractedTask(
                task="Направить отчёт по результатам аудита",
                responsible="Нурлан Сагатович",
                assigned_by="Асхат Ерланович",
                deadline_raw="после аудита",
                deadline_normalized=None,
                original_text="Отчёт направьте мне, после этого запускаем пилот.",
                confidence=0.86,
            ),
        ]

    def summarize(self, transcript: list[MergedSegment], tasks: list[ExtractedTask]) -> GeneratedSummary:
        return GeneratedSummary(
            topic="Готовность пилотного запуска системы мониторинга",
            key_points=[
                "Пилот охватывает 11 площадок.",
                "Два датчика требуют повторной проверки.",
                "Поставщик уведомлён о выявленных рисках.",
            ],
            problems=["Не подтверждена исправность двух датчиков."],
            decisions=["Провести аудит и запускать пилот после получения отчёта."],
        )

