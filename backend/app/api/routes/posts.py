import os
import uuid
from typing import Any, Optional

from fastapi import (
  APIRouter,
  HTTPException,
  Request,
  status,
)
from pydantic import BaseModel

from app.api.deps import AsyncSessionDep, TaskServiceDep
from app.schemas import (
  PostPublic,
  TaskCreate,
  TaskType,
)
from app.service.post_service import PostService
from app.utils.instagram import extract_shortcode_from_url

STREAM_NAME = os.getenv("REDIS_STREAM", "tasks:instagram_download:stream")

REDIS_CHANNEL_OUTPUT = "tasks:instagram_download:output"

router = APIRouter(prefix="/posts", tags=["posts"])


class PostImportRequest(BaseModel):
  url: str


@router.post("/", status_code=status.HTTP_200_OK)
async def create_post(
  *,
  request: Request,
  session: AsyncSessionDep,
  task_service: TaskServiceDep,
  obj_in: PostImportRequest,
) -> Any:
  """
  Import an Instagram post from a URL.

  This will fetch the post metadata from Instagram,
  create the author, post, and image records in the database.
  """

  post_service = PostService(session=session)

  try:
    task_id = uuid.uuid4()
    post_id = extract_shortcode_from_url(obj_in.url)

    if not post_id:
      raise HTTPException(status_code=404)

    existing_post = await post_service.get_post_by_id(post_id)
    if existing_post:
      return existing_post

    await post_service.create_post(post_id=post_id)

    await task_service.create_task(
      task_create=TaskCreate(
        id=task_id,
        type=TaskType.instagram_download,
        post_id=post_id,
      )
    )

    redis_client = request.app.state.redis_client
    await redis_client.xadd(
      STREAM_NAME,
      {
        "task_id": str(task_id),
        "url": obj_in.url,
      },
    )

    return {
      "task_id": task_id,
    }

  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.get("/{post_id}", response_model=Optional[PostPublic])
async def get_post_by_id(
  *,
  session: AsyncSessionDep,
  post_id: str,
) -> Any:
  post_service = PostService(session=session)

  return await post_service.get_post_by_id(post_id)
