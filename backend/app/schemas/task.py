from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import SQLModel


class TaskType(str, Enum):
  """Enum for task types."""

  llm_generate = "llm_generate"
  instagram_download = "instagram_download"


class TaskStatus(str, Enum):
  """Enum for task statuses."""

  pending = "pending"
  in_progress = "in_progress"
  done = "done"
  failed = "failed"
  skipped = "skipped"


class TaskBase(SQLModel):
  """Base schema for a task."""

  id: UUID
  type: TaskType
  post_id: str
  image_id: Optional[UUID] = None


class TaskCreate(TaskBase):
  """Schema for creating a new task."""

  user_id: UUID


class TaskPublic(TaskBase):
  """Public schema for a task."""

  id: UUID
  status: TaskStatus
  user_id: UUID
  created_at: Optional[datetime]
  updated_at: Optional[datetime]


class TaskUpdate(SQLModel):
  """Schema for updating a task."""

  status: Optional[TaskStatus] = None
  error_message: Optional[str] = None
  started_at: Optional[datetime] = None
  ended_at: Optional[datetime] = None
  duration: Optional[timedelta] = None
  updated_at: Optional[datetime] = None
