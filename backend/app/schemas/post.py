import uuid
from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel

from .image import ImagePublic


class PostCreate(SQLModel):
  """Schema for creating a new post."""

  author_id: uuid.UUID
  description: str
  taken_at: datetime


class PostPublic(SQLModel):
  """Public schema for a post."""

  id: str
  author_id: Optional[uuid.UUID] = None
  images: Optional[List[ImagePublic]] = None


class PostUpdate(SQLModel):
  """Schema for updating a post."""

  author_id: Optional[uuid.UUID] = None
  description: Optional[str] = None
  taken_at: Optional[datetime] = None
