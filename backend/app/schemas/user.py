from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
  """Base schema for a user."""

  email: EmailStr = Field(unique=True, index=True, max_length=255)
  is_active: bool = True
  is_superuser: bool = False
  full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
  """Schema for creating a new user."""

  password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
  """Schema for user registration."""

  email: EmailStr = Field(max_length=255)
  password: str = Field(min_length=8, max_length=40)
  full_name: str | None = Field(default=None, max_length=255)


class UserUpdate(UserBase):
  """Schema for updating a user."""

  email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
  password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
  """Schema for updating the current user."""

  full_name: str | None = Field(default=None, max_length=255)
  email: EmailStr | None = Field(default=None, max_length=255)


class UserPublic(UserBase):
  """Public schema for a user."""

  id: UUID


class UsersPublic(SQLModel):
  """Public schema for a list of users."""

  data: list[UserPublic]
  count: int
