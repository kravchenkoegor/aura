import uuid

from sqlmodel import SQLModel


class ImagePublic(SQLModel):
  """Public schema for an image."""

  id: uuid.UUID
  storage_key: str
  height: int
  width: int
  is_primary: bool
