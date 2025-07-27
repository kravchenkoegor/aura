from sqlmodel import SQLModel


class Token(SQLModel):
  token: str


# Contents of JWT token
class TokenPayload(SQLModel):
  sub: str | None = None
