import uuid
from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel

from .image import ImagePublic


class PostCreate(SQLModel):
  author_id: uuid.UUID
  description: str
  taken_at: datetime


class PostPublic(SQLModel):
  id: str
  author_id: Optional[uuid.UUID] = None
  images: Optional[List[ImagePublic]] = None


class PostUpdate(SQLModel):
  author_id: Optional[uuid.UUID] = None
  description: Optional[str] = None
  taken_at: Optional[datetime] = None
