from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.meeting import Participant, Task, TranscriptSegment
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import ParticipantRead, ParticipantUpdate

router = APIRouter(prefix="/meetings/{meeting_id}/participants", tags=["participants"])


@router.get("", response_model=list[ParticipantRead])
def list_participants(meeting_id: int, db: Session = Depends(get_db)):
    meeting = MeetingRepository(db).get(meeting_id, with_relations=True)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.participants


@router.patch("/{participant_id}", response_model=ParticipantRead)
def update_participant(
    meeting_id: int, participant_id: int, payload: ParticipantUpdate, db: Session = Depends(get_db)
):
    participant = db.get(Participant, participant_id)
    if not participant or participant.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Participant not found")
    old_name = participant.display_name
    if payload.display_name is not None:
        participant.display_name = payload.display_name
    if "role" in payload.model_fields_set:
        participant.role = payload.role.strip() if payload.role else None
    for segment in db.query(TranscriptSegment).filter(
        TranscriptSegment.meeting_id == meeting_id,
        TranscriptSegment.speaker_label == participant.speaker_label,
    ):
        if payload.display_name is not None:
            segment.speaker_name = payload.display_name
        if "role" in payload.model_fields_set:
            segment.speaker_role = participant.role
    if payload.display_name is not None and old_name != payload.display_name:
        for task in db.query(Task).filter(Task.meeting_id == meeting_id):
            if task.responsible == old_name:
                task.responsible = payload.display_name
            if task.assigned_by == old_name:
                task.assigned_by = payload.display_name
    db.commit()
    db.refresh(participant)
    return participant
