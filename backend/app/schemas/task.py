from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import SQLModel


class TaskType(str, Enum):
  llm_generate = "llm_generate"
  instagram_download = "instagram_download"


class TaskStatus(str, Enum):
  pending = "pending"
  in_progress = "in_progress"
  done = "done"
  failed = "failed"
  skipped = "skipped"


class TaskBase(SQLModel):
  id: UUID
  type: TaskType
  post_id: str
  image_id: Optional[UUID] = None


class TaskCreate(TaskBase):
  user_id: UUID


class TaskPublic(TaskBase):
  id: UUID
  status: TaskStatus
  user_id: UUID
  created_at: Optional[datetime]
  updated_at: Optional[datetime]


class TaskUpdate(SQLModel):
  status: Optional[TaskStatus] = None
  error_message: Optional[str] = None
  started_at: Optional[datetime] = None
  ended_at: Optional[datetime] = None
  duration: Optional[timedelta] = None
  updated_at: Optional[datetime] = None
