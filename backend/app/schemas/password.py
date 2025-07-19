from sqlmodel import Field, SQLModel


class NewPassword(SQLModel):
  token: str
  new_password: str = Field(min_length=8, max_length=40)


class UpdatePassword(SQLModel):
  current_password: str = Field(min_length=8, max_length=40)
  new_password: str = Field(min_length=8, max_length=40)
