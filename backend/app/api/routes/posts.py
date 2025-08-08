import os
from typing import Optional

from fastapi import (
  APIRouter,
  Request,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, PostServiceDep
from app.core.rate_limit import rate_limit_default
from app.schemas import PostPublic

STREAM_NAME = os.getenv("REDIS_STREAM", "tasks:instagram_download:stream")

REDIS_CHANNEL_OUTPUT = "tasks:instagram_download:output"

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/{post_id}", response_model=Optional[PostPublic])
@rate_limit_default
async def get_post_by_id(
  request: Request,
  *,
  current_user: CurrentUser,
  post_service: PostServiceDep,
  post_id: str,
) -> JSONResponse:
  """Get a post by its ID."""

  post_data = await post_service.get_post_by_id(
    post_id=post_id,
    user_id=current_user.id,
  )
  post = post_data.model_dump() if post_data else None

  return JSONResponse(content=jsonable_encoder(post))
