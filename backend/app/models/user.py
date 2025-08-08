from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship

from app.schemas.user import UserBase

if TYPE_CHECKING:
  from .post import Post
  from .task import Task


class User(UserBase, table=True):
  __tablename__ = "users"  # type: ignore

  id: UUID = Field(default_factory=uuid4, primary_key=True)
  hashed_password: str

  posts: Optional[List["Post"]] = Relationship(back_populates="user")
  tasks: Optional[List["Task"]] = Relationship(back_populates="user")
