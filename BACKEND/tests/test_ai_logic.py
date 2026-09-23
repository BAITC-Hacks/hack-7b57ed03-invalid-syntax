from datetime import date
from types import SimpleNamespace

from app.ai.contracts import SpeakerTurn, SpeechSegment
from app.ai.deadline_parser.parser import parse_deadline
from app.ai.pipelines.meeting import MeetingProcessingPipeline
from app.ai.providers.openai_provider import OpenAIAnalysis, OpenAIMeetingProvider, OpenAITask


def test_deadlines_are_relative_to_meeting_date():
    meeting = date(2026, 9, 23)
    assert parse_deadline("завтра", meeting) == date(2026, 9, 24)
    assert parse_deadline("до пятницы", meeting) == date(2026, 9, 25)
    assert parse_deadline("до конца месяца", meeting) == date(2026, 9, 30)
    assert parse_deadline("до 15 октября", meeting) == date(2026, 10, 15)
    assert parse_deadline("когда будет возможность", meeting) is None


def test_merge_uses_maximum_overlap_and_handles_empty_turns():
    speech = [SpeechSegment(0, 10, "text", 0.8)]
    turns = [SpeakerTurn(0, 2, "Speaker_01"), SpeakerTurn(2, 10, "Speaker_02")]
    merged = MeetingProcessingPipeline.merge_stt_and_diarization(speech, turns)
    assert merged[0].speaker_label == "Speaker_02"
    fallback = MeetingProcessingPipeline.merge_stt_and_diarization(speech, [])
    assert fallback[0].speaker_label == "Speaker_01"


def test_openai_provider_maps_diarization_and_structured_output(tmp_path):
    class FakeTranscriptions:
        def create(self, **kwargs):
            assert kwargs["model"] == "gpt-4o-transcribe-diarize"
            assert kwargs["response_format"] == "diarized_json"
            assert kwargs["chunking_strategy"] == "auto"
            return SimpleNamespace(segments=[
                SimpleNamespace(speaker="A", text="Ануар, подготовьте отчёт до пятницы.", start=1.0, end=4.5),
                SimpleNamespace(speaker="B", text="Принял.", start=4.6, end=5.4),
            ])

    class FakeResponses:
        def parse(self, **kwargs):
            assert kwargs["text_format"] is OpenAIAnalysis
            return SimpleNamespace(output_parsed=OpenAIAnalysis(
                topic="Отчёт",
                summary="Назначена подготовка отчёта.",
                key_points=["Нужен отчёт"],
                decisions=["Подготовить отчёт"],
                problems=[],
                tasks=[OpenAITask(
                    task="Подготовить отчёт", responsible="Спикер B", assigned_by="Спикер A",
                    deadline_raw="до пятницы", deadline_normalized="2026-09-25",
                    original_text="Ануар, подготовьте отчёт до пятницы.", confidence=0.97,
                )],
            ))

    fake_client = SimpleNamespace(
        audio=SimpleNamespace(transcriptions=FakeTranscriptions()),
        responses=FakeResponses(),
    )
    media = tmp_path / "meeting.wav"
    media.write_bytes(b"RIFF-test")
    provider = OpenAIMeetingProvider(client=fake_client)
    transcript = provider.transcribe_and_diarize(media)
    tasks, summary = provider.analyze(transcript, date(2026, 9, 23))

    assert [segment.speaker_label for segment in transcript] == ["A", "B"]
    assert transcript[0].speaker_name == "Спикер A"
    assert tasks[0].deadline_normalized == date(2026, 9, 25)
    assert summary.decisions == ["Подготовить отчёт"]
