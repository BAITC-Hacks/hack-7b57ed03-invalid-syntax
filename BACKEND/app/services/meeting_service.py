import json
from datetime import date

from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import MeetingRead, SummaryRead


class MeetingService:
    def __init__(self, db: Session):
        self.repo = MeetingRepository(db)

    def create(self, title: str, meeting_date: date) -> Meeting:
        return self.repo.add(Meeting(title=title, meeting_date=meeting_date))

    @staticmethod
    def to_read(meeting: Meeting) -> MeetingRead:
        summary = None
        if meeting.summary:
            summary = SummaryRead(
                topic=meeting.summary.topic,
                summary_text=meeting.summary.summary_text,
                key_points=json.loads(meeting.summary.key_points_json),
                problems=json.loads(meeting.summary.problems_json),
                decisions=json.loads(meeting.summary.decisions_json),
                risks=json.loads(meeting.summary.risks_json),
                metrics=json.loads(meeting.summary.metrics_json),
                tasks=[task.id for task in meeting.tasks],
            )
        return MeetingRead.model_validate(
            {
                "id": meeting.id,
                "title": meeting.title,
                "meeting_date": meeting.meeting_date,
                "status": meeting.status,
                "stage": meeting.stage,
                "progress": meeting.progress,
                "source_filename": meeting.source_filename,
                "created_at": meeting.created_at,
                "participants": meeting.participants,
                "transcript": meeting.transcript,
                "tasks": meeting.tasks,
                "summary": summary,
            }
        )
