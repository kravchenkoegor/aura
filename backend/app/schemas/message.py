from sqlmodel import SQLModel


class Message(SQLModel):
  """Schema for a message."""

  message: str
