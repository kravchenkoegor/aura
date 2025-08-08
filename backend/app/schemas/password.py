from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class NewPassword(SQLModel):
  """Schema for setting a new password."""

  token: str
  new_password: str = Field(min_length=8, max_length=40)


class UpdatePassword(SQLModel):
  """Schema for updating a password."""

  current_password: str = Field(min_length=8, max_length=40)
  new_password: str = Field(min_length=8, max_length=40)


class ForgotPassword(SQLModel):
  """Schema for requesting a password reset."""

  email: EmailStr
