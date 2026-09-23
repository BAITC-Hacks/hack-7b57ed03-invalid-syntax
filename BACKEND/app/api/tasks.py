from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.meeting import Task
from app.repositories.meeting_repository import MeetingRepository
from app.schemas.meeting import TaskRead, TaskUpdate

router = APIRouter(prefix="/meetings/{meeting_id}/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead])
def list_tasks(meeting_id: int, db: Session = Depends(get_db)):
    meeting = MeetingRepository(db).get(meeting_id, with_relations=True)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting.tasks


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(meeting_id: int, task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task or task.meeting_id != meeting_id:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task

