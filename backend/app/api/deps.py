from typing import Annotated, AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.db import async_session
from app.models import User
from app.schemas import TokenPayload, UserPublic
from app.service import (
  ComplimentService,
  GeminiService,
  ImageService,
  PostService,
  TaskService,
)

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/login/access-token")


async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
  async with async_session() as session:
    yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_db_async)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def get_current_user(
  session: AsyncSessionDep,
  token: TokenDep,
) -> UserPublic:
  try:
    payload = jwt.decode(
      token,
      settings.SECRET_KEY,
      algorithms=[security.ALGORITHM],
    )
    token_data = TokenPayload(**payload)

  except (InvalidTokenError, ValidationError):
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Could not validate credentials",
    )

  user = await session.get(User, token_data.sub)

  if not user:
    raise HTTPException(status_code=404, detail="User not found")

  if not user.is_active:
    raise HTTPException(status_code=400, detail="Inactive user")

  return UserPublic.model_validate(user)


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
  if not current_user.is_superuser:
    raise HTTPException(
      status_code=403, detail="The user doesn't have enough privileges"
    )
  return current_user


def get_compliment_service(session: AsyncSessionDep) -> ComplimentService:
  return ComplimentService(session=session)


ComplimentServiceDep = Annotated[ComplimentService, Depends(get_compliment_service)]


def get_gemini_service(session: AsyncSessionDep) -> GeminiService:
  return GeminiService(session=session)


GeminiServiceDep = Annotated[GeminiService, Depends(get_gemini_service)]


def get_image_service(session: AsyncSessionDep) -> ImageService:
  return ImageService(session=session)


ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]


def get_post_service(session: AsyncSessionDep) -> PostService:
  return PostService(session=session)


PostServiceDep = Annotated[PostService, Depends(get_post_service)]


def get_task_service(session: AsyncSessionDep) -> TaskService:
  return TaskService(session=session)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
