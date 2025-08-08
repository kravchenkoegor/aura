from pydantic import BaseModel, Field


class Comment(BaseModel):
  """Schema for a comment."""

  text: str
  language: str


class ToneBreakdown(BaseModel):
  """Schema for the tone breakdown of a compliment."""

  poetic: int
  romantic: int
  flirtatious: int
  witty: int
  curious: int


class Analysis(BaseModel):
  """Schema for the analysis of a compliment."""

  rationale: str
  approach_used: str
  tone_breakdown: ToneBreakdown = Field(..., alias="tone_breakdown")


class ComplimentOutput(BaseModel):
  """Schema for the output of a compliment generation."""

  comment: Comment
  analysis: Analysis
