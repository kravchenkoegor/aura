import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
  Column,
  Interval,
)
from sqlalchemy import (
  Enum as PgEnum,
)
from sqlmodel import (
  Field,
  Relationship,
  SQLModel,
)

from app.schemas.task import TaskStatus, TaskType
from app.utils.utc_now import utc_now

if TYPE_CHECKING:
  from .image import Image
  from .post import Post


class Task(SQLModel, table=True):
  __tablename__ = "tasks"  # type: ignore

  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
  type: TaskType
  status: TaskStatus = Field(
    sa_column=Column(
      PgEnum(TaskStatus, name="taskstatus", create_type=True),
      nullable=False,
      server_default=TaskStatus.pending.value,
    )
  )
  error_message: Optional[str] = None
  started_at: Optional[datetime] = None
  ended_at: Optional[datetime] = None
  duration: Optional[timedelta] = Field(
    default=None,
    sa_column=Column(Interval),
  )

  post_id: Optional[str] = Field(default=None, foreign_key="posts.id")
  post: Optional["Post"] = Relationship(back_populates="tasks")

  image_id: Optional[uuid.UUID] = Field(default=None, foreign_key="images.id")
  image: Optional["Image"] = Relationship(back_populates="tasks")

  created_at: datetime = Field(default_factory=utc_now)
  updated_at: Optional[datetime] = None
