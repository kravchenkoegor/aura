from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlmodel import Column, Field, Relationship, SQLModel


if TYPE_CHECKING:
  from .compliment import Compliment


class Language(SQLModel, table=True):
  '''Lookup table for supported languages.'''

  __tablename__ = 'languages'  # type: ignore

  id: str = Field(sa_column=Column(String(2), primary_key=True))
  name: str = Field(
    sa_column=Column(
      String(64),
      nullable=False,
      comment='e.g., "English", "Spanish"',
    ),
  )

  # Relationship: A language can be used in many compliments
  compliments: list['Compliment'] = Relationship(back_populates='language')

  def __repr__(self):
    return f'<Language(id={self.id}, name=\'{self.name}\')>'
