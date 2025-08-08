from sqlmodel import SQLModel


class Token(SQLModel):
  """Schema for a token."""

  token: str


class TokenPayload(SQLModel):
  """Schema for the payload of a JWT token."""

  sub: str | None = None
