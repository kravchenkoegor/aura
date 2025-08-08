from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
  TIMESTAMP,
  Column,
  Interval,
)
from sqlalchemy import Enum as PgEnum
from sqlmodel import (
  Field,
  Relationship,
  SQLModel,
  func,
)

from app.schemas.task import TaskStatus, TaskType

if TYPE_CHECKING:
  from .image import Image
  from .post import Post
  from .user import User


class Task(SQLModel, table=True):
  """Represents a background task to be executed."""

  __tablename__ = "tasks"  # type: ignore

  id: UUID = Field(
    default_factory=uuid4,
    primary_key=True,
    index=True,
  )
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

  image_id: Optional[UUID] = Field(default=None, foreign_key="images.id")
  image: Optional["Image"] = Relationship(back_populates="tasks")

  user_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)
  user: Optional["User"] = Relationship(back_populates="tasks")

  created_at: datetime = Field(
    sa_column=Column(
      TIMESTAMP(timezone=True),
      server_default=func.now(),
      nullable=False,
    ),
  )
  updated_at: Optional[datetime] = None
