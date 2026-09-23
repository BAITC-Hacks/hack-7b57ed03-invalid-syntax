from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.meeting import Meeting


class MeetingRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[Meeting]:
        return list(self.db.scalars(select(Meeting).order_by(Meeting.created_at.desc())))

    def get(self, meeting_id: int, with_relations: bool = False) -> Meeting | None:
        statement = select(Meeting).where(Meeting.id == meeting_id)
        if with_relations:
            statement = statement.options(
                selectinload(Meeting.participants),
                selectinload(Meeting.transcript),
                selectinload(Meeting.tasks),
                selectinload(Meeting.summary),
            )
        return self.db.scalar(statement)

    def add(self, meeting: Meeting) -> Meeting:
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting

    def save(self, meeting: Meeting) -> Meeting:
        self.db.add(meeting)
        self.db.commit()
        self.db.refresh(meeting)
        return meeting

