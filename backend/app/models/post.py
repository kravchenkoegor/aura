import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TIMESTAMP, Column, Text
from sqlmodel import Field, Relationship, SQLModel

from app.utils.utc_now import utc_now

if TYPE_CHECKING:
  from .author import Author
  from .image import Image
  from .task import Task


class Post(SQLModel, table=True):
  """Represents a single imported Instagram post."""

  __tablename__ = "posts"  # type: ignore

  id: str = Field(primary_key=True, index=True)
  author_id: Optional[uuid.UUID] = Field(
    default=None,
    foreign_key="authors.id",
    nullable=True,
    ondelete="RESTRICT",
  )
  description: Optional[str] = Field(sa_column=Column(Text, nullable=True))
  taken_at: Optional[datetime] = Field(
    sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
  )
  created_at: datetime = Field(
    default_factory=utc_now,
    sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
  )

  # Relationship: A post belongs to one author
  author: "Author" = Relationship(back_populates="posts")

  # Relationship: A post can have many images (e.g., a carousel)
  images: list["Image"] = Relationship(
    back_populates="post", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
  )

  tasks: list["Task"] = Relationship(
    back_populates="post",
    sa_relationship_kwargs={"cascade": "all, delete-orphan"},
  )

  def __repr__(self):
    return f"<Post(id={self.id})>"
