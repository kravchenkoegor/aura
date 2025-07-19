import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Relationship, SQLModel

from app.utils.utc_now import utc_now

if TYPE_CHECKING:
  from .generation_metadata import GenerationMetadata
  from .image import Image
  from .language import Language


class Compliment(SQLModel, table=True):
  """
  Represents the final, generated compliment for a specific image.
  This is the core creative output of the application.
  """

  __tablename__ = "compliments"  # type: ignore

  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  image_id: uuid.UUID = Field(
    foreign_key="images.id",
    nullable=False,
    ondelete="CASCADE",
  )
  lang_id: str = Field(
    foreign_key="languages.id",
    nullable=False,
    ondelete="RESTRICT",
  )
  generation_id: uuid.UUID = Field(
    foreign_key="generation_metadata.id",
    nullable=False,
    ondelete="RESTRICT",
  )
  text: str = Field(sa_column=Column(Text, nullable=False))
  tone_breakdown: dict | None = Field(default=None, sa_column=Column(JSONB))
  created_at: datetime = Field(
    default_factory=utc_now,
    sa_column=Column(TIMESTAMP(timezone=True), nullable=False),
  )

  # Relationship: A compliment is for one image
  image: "Image" = Relationship(back_populates="compliments")

  # Relationship: A compliment is in one language
  language: "Language" = Relationship(back_populates="compliments")

  # Relationship: A compliment has one set of generation metadata
  generation_metadata: "GenerationMetadata" = Relationship(back_populates="compliments")

  def __repr__(self):
    return f"<Compliment(id={self.id}, image_id={self.image_id})>"
