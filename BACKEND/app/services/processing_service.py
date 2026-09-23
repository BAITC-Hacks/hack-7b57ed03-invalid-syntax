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
            transcript, tasks, summary = pipeline.run(Path(meeting.source_path), meeting.meeting_date)
            meeting = repo.get(meeting_id, with_relations=True)
            if not meeting:
                return

            meeting.participants.clear()
            meeting.transcript.clear()
            meeting.tasks.clear()
            if meeting.summary:
                db.delete(meeting.summary)
            db.flush()

            participant_names: dict[str, str] = {}
            for segment in transcript:
                participant_names[segment.speaker_label] = segment.speaker_name
                meeting.transcript.append(
                    TranscriptSegment(
                        speaker_label=segment.speaker_label,
                        speaker_name=segment.speaker_name,
                        start=segment.start,
                        end=segment.end,
                        text=segment.text,
                    )
                )
            for label, name in participant_names.items():
                meeting.participants.append(
                    Participant(speaker_label=label, display_name=name, confidence=0.91)
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
            meeting.summary = Summary(
                topic=summary.topic,
                key_points_json=json.dumps(summary.key_points, ensure_ascii=False),
                problems_json=json.dumps(summary.problems, ensure_ascii=False),
                decisions_json=json.dumps(summary.decisions, ensure_ascii=False),
            )
            meeting.status = "completed"
            meeting.stage = "completed"
            meeting.progress = 100
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

