import uuid

from datetime import datetime, timedelta
from enum import Enum
from sqlmodel import SQLModel
from typing import Optional


class TaskType(str, Enum):
  llm_generate = 'llm_generate'
  instagram_download = 'instagram_download'


class TaskStatus(str, Enum):
  pending = 'pending'
  in_progress = 'in_progress'
  done = 'done'
  failed = 'failed'
  skipped = 'skipped'


class TaskBase(SQLModel):
  id: uuid.UUID
  type: TaskType
  post_id: str
  image_id: Optional[uuid.UUID] = None


class TaskCreate(TaskBase):
  pass


class TaskPublic(TaskBase):
  id: uuid.UUID
  status: TaskStatus
  created_at: Optional[datetime]
  updated_at: Optional[datetime]


class TaskUpdate(SQLModel):
  status: Optional[TaskStatus] = None
  error_message: Optional[str] = None
  started_at: Optional[datetime] = None
  ended_at: Optional[datetime] = None
  duration: Optional[timedelta] = None
  updated_at: Optional[datetime] = None
