from typing import Annotated, AsyncGenerator

import jwt
from fastapi import (
  Depends,
  HTTPException,
  Request,
  WebSocket,
  WebSocketDisconnect,
  status,
)
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import security
from app.core.config import settings
from app.core.db import async_session
from app.models import User
from app.schemas import TokenPayload
from app.service import (
  ComplimentService,
  GeminiService,
  ImageService,
  PostService,
  TaskService,
)

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/login/access-token")


async def get_db_async() -> AsyncGenerator[AsyncSession, None]:
  """Get an async database session."""

  async with async_session() as session:
    yield session


AsyncSessionDep = Annotated[AsyncSession, Depends(get_db_async)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]


async def _get_user_from_token(token: str, session: AsyncSession) -> User:
  """
  Decodes a JWT token, validates it, and returns the corresponding user.
  Raises HTTPException on failure.
  """

  if not token:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Not authenticated",
    )

  try:
    payload = jwt.decode(
      token,
      settings.security.SECRET_KEY,
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
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Could not validate credentials",
    )

  if not user.is_active:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Inactive user",
    )

  return user


async def get_current_user(
  session: AsyncSessionDep,
  token: TokenDep,
  request: Request,
) -> User:
  """Get the current user from a token."""

  try:
    payload = jwt.decode(
      token,
      settings.security.SECRET_KEY,
      algorithms=[security.ALGORITHM],
    )
    token_data = TokenPayload(**payload)

  except (InvalidTokenError, ValidationError) as e:
    print(str(e))
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Incorrect email or password",
    )

  user = await session.get(User, token_data.sub)

  if not user:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="Incorrect email or password",
    )

  if not user.is_active:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Inactive user",
    )

  request.state.user = user

  return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_user_ws(
  websocket: WebSocket,
  session: AsyncSessionDep,
  token: str | None = None,
) -> User:
  """
  Dependency for WebSocket authentication.
  Gets token from query params and validates the user.
  """
  if not token:
    token = websocket.query_params.get("token")

  if not token:
    await websocket.close(
      code=status.WS_1008_POLICY_VIOLATION,
      reason="Missing token",
    )
    raise WebSocketDisconnect()

  try:
    user = await _get_user_from_token(token=token, session=session)
    return user

  except HTTPException as e:
    reason = e.detail
    code = status.WS_1008_POLICY_VIOLATION

    if e.status_code == status.HTTP_403_FORBIDDEN:
      reason = "Token is invalid"

    elif e.status_code == status.HTTP_400_BAD_REQUEST:
      reason = "Inactive user"

    await websocket.close(code=code, reason=reason)
    raise WebSocketDisconnect() from e


CurrentUserWS = Annotated[User, Depends(get_current_user_ws)]


def get_current_active_superuser(current_user: CurrentUser) -> User:
  """Get the current active superuser."""

  if not current_user.is_superuser:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

  return current_user


def get_compliment_service(session: AsyncSessionDep) -> ComplimentService:
  """Get the compliment service."""

  return ComplimentService(session=session)


ComplimentServiceDep = Annotated[ComplimentService, Depends(get_compliment_service)]


def get_gemini_service(session: AsyncSessionDep) -> GeminiService:
  """Get the Gemini service."""

  return GeminiService(session=session)


GeminiServiceDep = Annotated[GeminiService, Depends(get_gemini_service)]


def get_image_service(session: AsyncSessionDep) -> ImageService:
  """Get the image service."""

  return ImageService(session=session)


ImageServiceDep = Annotated[ImageService, Depends(get_image_service)]


def get_post_service(session: AsyncSessionDep) -> PostService:
  """Get the post service."""

  return PostService(session=session)


PostServiceDep = Annotated[PostService, Depends(get_post_service)]


def get_task_service(session: AsyncSessionDep) -> TaskService:
  """Get the task service."""

  return TaskService(session=session)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
