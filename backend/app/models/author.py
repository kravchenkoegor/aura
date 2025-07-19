from typing import TYPE_CHECKING

import uuid
from datetime import datetime
from sqlalchemy import TIMESTAMP, Column
from sqlmodel import Field, Relationship, SQLModel

from app.utils.utc_now import utc_now

if TYPE_CHECKING:
  from .post import Post


class Author(SQLModel, table=True):
  '''Represents an author of posts, normalized from the posts table.'''

  __tablename__ = 'authors'  # type: ignore

  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  username: str = Field(max_length=255)
  created_at: datetime = Field(
    default_factory=utc_now,
    sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
  )

  # Relationship: An author can have many posts
  posts: list['Post'] = Relationship(
    back_populates='author',
    sa_relationship_kwargs={'cascade': 'all, delete-orphan'}
  )

  def __repr__(self):
    return f'<Author(id={self.id}, username=\'{self.username}\')>'
