import uuid

from pydantic import BaseModel, Field
from sqlmodel import SQLModel


class ComplimentPublic(SQLModel):
  """
  Public representation of a compliment, suitable for API responses.
  Excludes sensitive or internal data.
  """

  id: uuid.UUID
  lang_id: str
  text: str
  tone_breakdown: dict | None = None

  def __repr__(self):
    return f"<ComplimentPublic(id={self.id})>"


class ComplimentRequest(BaseModel):
  post_id: str = Field(
    ...,
    min_length=6,
    max_length=11,
    pattern=r"^[A-Za-z0-9_-]+$",
    description="Instagram post shortcode (e.g. BQvCZO6hXzv)",
  )
  style: str = Field(
    default="romantic",
    pattern=r"^(romantic|poetic|flirtatious|witty|curious|casual|playful)$",
    description="Style of compliment to generate",
  )


class TranslateRequest(BaseModel):
  target_language: str = Field(
    ...,
    min_length=2,
    max_length=10,
    pattern=r"^[a-z]{2,10}$",
    description="Target language code (e.g., 'tr' for Turkish, 'es' for Spanish)",
    examples=["tr", "es", "fr", "de"],
  )


class TranslateResponse(BaseModel):
  compliment_id: uuid.UUID
  original_text: str
  original_language: str
  translated_text: str
  target_language: str
