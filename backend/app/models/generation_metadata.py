import uuid
from datetime import datetime
from sqlalchemy import TIMESTAMP, Column, Integer, Text
from sqlmodel import Field, Relationship, SQLModel
from typing import TYPE_CHECKING

from app.utils.utc_now import utc_now


if TYPE_CHECKING:
  from .compliment import Compliment


class GenerationMetadata(SQLModel, table=True):
  '''
  Stores technical metadata about an AI model invocation.
  This separates the 'how' from the 'what'.
  '''

  __tablename__ = 'generation_metadata'  # type: ignore

  id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
  model_used: str = Field(
    sa_column=Column(
      Text,
      nullable=False,
      comment='The AI model used for generation (e.g., Gemini 2.5 Pro, Flash)',
    ),
  )
  prompt_token_count: int = Field(sa_column=Column(Integer, nullable=False))
  candidates_token_count: int = Field(
    sa_column=Column(Integer, nullable=False)
  )
  total_token_count: int = Field(sa_column=Column(Integer, nullable=False))
  analysis_duration_ms: int = Field(sa_column=Column(Integer, nullable=False))
  created_at: datetime = Field(
    default_factory=utc_now,
    sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
  )

  # Relationship: This metadata is associated with multiple generated compliment
  compliments: list['Compliment'] = Relationship(
    back_populates='generation_metadata',
    sa_relationship_kwargs={'uselist': False},
  )

  def __repr__(self):
    return f'<GenerationMetadata(id={self.id}, model=\'{self.model_used}\')>'
