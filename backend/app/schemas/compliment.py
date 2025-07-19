import uuid

from sqlmodel import SQLModel


class ComplimentPublic(SQLModel):
  '''
  Public representation of a compliment, suitable for API responses.
  Excludes sensitive or internal data.
  '''

  id: uuid.UUID
  lang_id: str
  text: str
  tone_breakdown: dict | None = None

  def __repr__(self):
    return f'<ComplimentPublic(id={self.id})>'
