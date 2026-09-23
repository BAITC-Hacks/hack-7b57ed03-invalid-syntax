import json
from pathlib import Path

from app.ai.pipelines.meeting import MeetingProcessingPipeline
from app.core.database import SessionLocal
from app.models.meeting import Participant, Summary, Task, TranscriptSegment
from app.repositories.meeting_repository import MeetingRepository


class ProcessingService:
    """Owns persistence around the replaceable AI pipeline."""

    @staticmethod
    def process(meeting_id: int) -> None:
        db = SessionLocal()
        repo = MeetingRepository(db)
        try:
            meeting = repo.get(meeting_id, with_relations=True)
            if not meeting or not meeting.source_path:
                raise ValueError("Meeting or uploaded media was not found")

            meeting.status = "processing"
            meeting.error = None
            repo.save(meeting)

            def update(stage: str, progress: int) -> None:
                current = repo.get(meeting_id)
                if current:
                    current.status = "processing"
                    current.stage = stage
                    current.progress = progress
                    repo.save(current)

            pipeline = MeetingProcessingPipeline(update)
            result = pipeline.run(Path(meeting.source_path), meeting.meeting_date)
            transcript, tasks, summary = result.transcript, result.tasks, result.summary
            meeting = repo.get(meeting_id, with_relations=True)
            if not meeting:
                return

            meeting.participants.clear()
            meeting.transcript.clear()
            meeting.tasks.clear()
            if meeting.summary:
                db.delete(meeting.summary)
            db.flush()

            participant_names: dict[str, tuple[str, str | None, float]] = {}
            for segment in transcript:
                participant_names[segment.speaker_label] = (
                    segment.speaker_name, segment.speaker_role, segment.speaker_confidence
                )
                meeting.transcript.append(
                    TranscriptSegment(
                        speaker_label=segment.speaker_label,
                        speaker_name=segment.speaker_name,
                        speaker_role=segment.speaker_role,
                        start=segment.start,
                        end=segment.end,
                        text=segment.text,
                        confidence=segment.confidence,
                    )
                )
            for label, (name, role, confidence) in participant_names.items():
                meeting.participants.append(
                    Participant(speaker_label=label, display_name=name, role=role, confidence=confidence)
                )
            for item in tasks:
                meeting.tasks.append(
                    Task(
                        task=item.task,
                        responsible=item.responsible,
                        assigned_by=item.assigned_by,
                        deadline_raw=item.deadline_raw,
                        deadline_normalized=item.deadline_normalized,
                        original_text=item.original_text,
                        confidence=item.confidence,
                    )
                )
            if summary:
                meeting.summary = Summary(
                    topic=summary.topic, summary_text=summary.summary_text,
                    key_points_json=json.dumps(summary.key_points, ensure_ascii=False),
                    problems_json=json.dumps(summary.problems, ensure_ascii=False),
                    decisions_json=json.dumps(summary.decisions, ensure_ascii=False),
                    risks_json=json.dumps(summary.risks or [], ensure_ascii=False),
                    metrics_json=json.dumps(summary.metrics or [], ensure_ascii=False),
                )
            meeting.status = "partial" if result.warnings else "completed"
            meeting.stage = "completed_with_warnings" if result.warnings else "completed"
            meeting.progress = 100
            meeting.error = "\n".join(result.warnings) or None
            repo.save(meeting)
        except Exception as exc:
            db.rollback()
            failed = repo.get(meeting_id)
            if failed:
                failed.status = "failed"
                failed.stage = "failed"
                failed.error = str(exc)
                repo.save(failed)
        finally:
            db.close()
