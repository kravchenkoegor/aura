from pydantic import BaseModel, Field


class Comment(BaseModel):
  text: str
  language: str


class ToneBreakdown(BaseModel):
  poetic: int
  romantic: int
  flirtatious: int
  witty: int
  curious: int


class Analysis(BaseModel):
  rationale: str
  approach_used: str
  tone_breakdown: ToneBreakdown = Field(..., alias='tone_breakdown')


class ComplimentOutput(BaseModel):
  comment: Comment
  analysis: Analysis
