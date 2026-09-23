import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.meeting_repository import MeetingRepository
from app.services.export_service import ExportService

router = APIRouter(prefix="/meetings/{meeting_id}/export", tags=["export"])


def export_meeting(db: Session, meeting_id: int):
    meeting = MeetingRepository(db).get(meeting_id, with_relations=True)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting.status not in {"completed", "partial"}:
        raise HTTPException(status_code=409, detail="Meeting processing is not complete")
    return meeting


@router.get("/pdf")
def export_pdf(meeting_id: int, db: Session = Depends(get_db)):
    meeting = export_meeting(db, meeting_id)
    try:
        content = ExportService().pdf(meeting)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"EXPORT_FAILED: Не удалось сформировать PDF: {exc}") from exc
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="meeting-{meeting_id}.pdf"'},
    )


@router.get("/docx")
def export_docx(meeting_id: int, db: Session = Depends(get_db)):
    meeting = export_meeting(db, meeting_id)
    try:
        content = ExportService().docx(meeting)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"EXPORT_FAILED: Не удалось сформировать DOCX: {exc}") from exc
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="meeting-{meeting_id}.docx"'},
    )
