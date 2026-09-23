from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import (
    MeetingCreate,
    MeetingListItem,
    MeetingRead,
    MeetingStatus,
    ProcessResponse,
    SummaryRead,
    TranscriptRead,
    UploadResponse,
)
from app.services.meeting_service import MeetingService
from app.services.processing_service import ProcessingService

router = APIRouter(prefix="/meetings", tags=["meetings"])


def get_meeting_or_404(db: Session, meeting_id: int, relations: bool = False):
    meeting = MeetingRepository(db).get(meeting_id, with_relations=relations)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("", response_model=list[MeetingListItem])
def list_meetings(db: Session = Depends(get_db)):
    return MeetingRepository(db).list()


@router.post("", response_model=MeetingListItem, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)):
    return MeetingService(db).create(payload.title, payload.meeting_date)


@router.post("/{meeting_id}/upload", response_model=UploadResponse)
def upload_media(meeting_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, meeting_id)
    suffix = Path(file.filename or "recording").suffix.lower()
    allowed = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}
    if suffix not in allowed:
        raise HTTPException(status_code=415, detail="Поддерживаются: FLAC, MP3, MP4, MPEG, MPGA, M4A, OGG, WAV, WEBM")
    if file.content_type and not (
        file.content_type.startswith("audio/") or file.content_type.startswith("video/")
        or file.content_type in {"application/octet-stream", "application/ogg"}
    ):
        raise HTTPException(status_code=415, detail="Файл не распознан как аудио или видео")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    target = settings.upload_dir / f"{meeting_id}_{uuid4().hex}{suffix}"
    size = 0
    with target.open("wb") as destination:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                destination.close()
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File is too large")
            destination.write(chunk)
    meeting.source_filename = file.filename
    meeting.source_path = str(target.resolve())
    meeting.status = "uploaded"
    meeting.stage = "uploaded"
    meeting.progress = 0
    MeetingRepository(db).save(meeting)
    return UploadResponse(meeting_id=meeting.id, filename=file.filename or target.name, status="uploaded")


@router.post("/{meeting_id}/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED)
def process_meeting(meeting_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, meeting_id)
    if not meeting.source_path:
        raise HTTPException(status_code=409, detail="Upload media before processing")
    if meeting.status == "processing":
        raise HTTPException(status_code=409, detail="Meeting is already being processed")
    meeting.status = "processing"
    meeting.stage = "queued"
    meeting.progress = 1
    MeetingRepository(db).save(meeting)
    background.add_task(ProcessingService.process, meeting_id)
    return ProcessResponse(meeting_id=meeting_id, status="processing", message="Processing started")


@router.get("/{meeting_id}/status", response_model=MeetingStatus)
def meeting_status(meeting_id: int, db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, meeting_id)
    return MeetingStatus(
        meeting_id=meeting.id,
        status=meeting.status,
        stage=meeting.stage,
        progress=meeting.progress,
        error=meeting.error,
    )


@router.get("/{meeting_id}/media")
def meeting_media(meeting_id: int, db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, meeting_id)
    if not meeting.source_path:
        raise HTTPException(status_code=404, detail="Media is not uploaded")
    path = Path(meeting.source_path).resolve()
    if not path.is_relative_to(settings.upload_dir.resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    return FileResponse(path)


@router.get("/{meeting_id}", response_model=MeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, meeting_id, relations=True)
    return MeetingService.to_read(meeting)


@router.get("/{meeting_id}/transcript", response_model=list[TranscriptRead])
def get_transcript(meeting_id: int, db: Session = Depends(get_db)):
    return get_meeting_or_404(db, meeting_id, relations=True).transcript


@router.get("/{meeting_id}/summary", response_model=SummaryRead)
def get_summary(meeting_id: int, db: Session = Depends(get_db)):
    meeting = get_meeting_or_404(db, meeting_id, relations=True)
    if not meeting.summary:
        raise HTTPException(status_code=404, detail="Summary is not ready")
    result = MeetingService.to_read(meeting).summary
    if result is None:
        raise HTTPException(status_code=404, detail="Summary is not ready")
    return result
