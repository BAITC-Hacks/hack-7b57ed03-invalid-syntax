from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MeetingCreate(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    meeting_date: date = Field(default_factory=date.today)


class MeetingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    meeting_date: date
    status: str
    stage: str
    progress: int
    source_filename: str | None
    created_at: datetime


class MeetingStatus(BaseModel):
    meeting_id: int
    status: str
    stage: str
    progress: int
    error: str | None = None


class ParticipantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    speaker_label: str
    display_name: str
    role: str | None = None
    confidence: float


class ParticipantUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=240)
    role: str | None = Field(default=None, max_length=300)


class TranscriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    speaker_label: str
    speaker_name: str
    speaker_role: str | None = None
    start: float
    end: float
    text: str
    confidence: float = 0.0


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task: str
    responsible: str
    assigned_by: str
    deadline_raw: str | None
    deadline_normalized: date | None
    original_text: str
    confidence: float
    status: str


class TaskUpdate(BaseModel):
    task: str | None = None
    responsible: str | None = None
    assigned_by: str | None = None
    deadline_normalized: date | None = None
    status: str | None = None

    @classmethod
    def allowed_statuses(cls) -> set[str]:
        return {"open", "confirmed", "done"}


class SummaryRead(BaseModel):
    topic: str
    summary_text: str
    key_points: list[str]
    problems: list[str]
    decisions: list[str]
    risks: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    tasks: list[int]


class MeetingRead(MeetingListItem):
    participants: list[ParticipantRead]
    transcript: list[TranscriptRead]
    tasks: list[TaskRead]
    summary: SummaryRead | None


class UploadResponse(BaseModel):
    meeting_id: int
    filename: str
    status: str


class ProcessResponse(BaseModel):
    meeting_id: int
    status: str
    message: str
