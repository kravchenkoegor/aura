import uuid

from sqlmodel import Field

from app.schemas.user import UserBase


class User(UserBase, table=True):
  __tablename__ = "users"  # type: ignore

  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  hashed_password: str
