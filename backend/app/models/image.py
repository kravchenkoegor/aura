import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, Text
from sqlmodel import Field, Relationship, SQLModel

from app.utils.utc_now import utc_now

if TYPE_CHECKING:
  from .compliment import Compliment
  from .post import Post
  from .task import Task


class Image(SQLModel, table=True):
  """Represents an image file associated with a post."""

  __tablename__ = "images"  # type: ignore

  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  post_id: str = Field(
    foreign_key="posts.id",
    nullable=False,
    ondelete="CASCADE",
  )
  storage_key: str = Field(
    # filename from instagram
    sa_column=Column(Text, nullable=False, unique=True)
  )
  height: int = Field(sa_column=Column(Integer, nullable=False))
  width: int = Field(sa_column=Column(Integer, nullable=False))
  is_primary: bool = Field(
    sa_column=Column(
      Boolean,
      nullable=False,
      default=False,
      comment="To mark the main image of a carousel",
    ),
  )
  created_at: datetime = Field(
    default_factory=utc_now,
    sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
  )

  # Relationship: An image belongs to one post
  post: "Post" = Relationship(back_populates="images")

  # Relationship: An image can have multiple compliment generated for it
  compliments: list["Compliment"] = Relationship(
    back_populates="image",
    sa_relationship_kwargs={
      "uselist": False,
      "cascade": "all, delete-orphan",
    },
  )

  tasks: list["Task"] = Relationship(
    back_populates="image", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
  )

  def __repr__(self):
    return f"<Image(id={self.id}, storage_key='{self.storage_key}')>"
