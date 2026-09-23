from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    meeting_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    stage: Mapped[str] = mapped_column(String(64), default="created")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    source_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    participants: Mapped[list[Participant]] = relationship(cascade="all, delete-orphan", back_populates="meeting")
    transcript: Mapped[list[TranscriptSegment]] = relationship(cascade="all, delete-orphan", back_populates="meeting")
    tasks: Mapped[list[Task]] = relationship(cascade="all, delete-orphan", back_populates="meeting")
    summary: Mapped[Summary | None] = relationship(cascade="all, delete-orphan", back_populates="meeting", uselist=False)


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    speaker_label: Mapped[str] = mapped_column(String(80))
    display_name: Mapped[str] = mapped_column(String(240))
    role: Mapped[str | None] = mapped_column(String(300), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    meeting: Mapped[Meeting] = relationship(back_populates="participants")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    speaker_label: Mapped[str] = mapped_column(String(80))
    speaker_name: Mapped[str] = mapped_column(String(240))
    speaker_role: Mapped[str | None] = mapped_column(String(300), nullable=True)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    meeting: Mapped[Meeting] = relationship(back_populates="transcript")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    task: Mapped[str] = mapped_column(Text)
    responsible: Mapped[str] = mapped_column(String(240))
    assigned_by: Mapped[str] = mapped_column(String(240))
    deadline_raw: Mapped[str | None] = mapped_column(String(240), nullable=True)
    deadline_normalized: Mapped[date | None] = mapped_column(Date, nullable=True)
    original_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="open")
    meeting: Mapped[Meeting] = relationship(back_populates="tasks")


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"), unique=True)
    topic: Mapped[str] = mapped_column(Text)
    summary_text: Mapped[str] = mapped_column(Text, default="")
    key_points_json: Mapped[str] = mapped_column(Text, default="[]")
    problems_json: Mapped[str] = mapped_column(Text, default="[]")
    decisions_json: Mapped[str] = mapped_column(Text, default="[]")
    risks_json: Mapped[str] = mapped_column(Text, default="[]")
    metrics_json: Mapped[str] = mapped_column(Text, default="[]")
    meeting: Mapped[Meeting] = relationship(back_populates="summary")
