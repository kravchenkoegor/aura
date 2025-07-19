import logging
import os
import uuid

from fastapi import (
  APIRouter,
  HTTPException,
  Request,
  status,
)
from pydantic import BaseModel

from app.api.deps import AsyncSessionDep
from app.schemas import (
  TaskCreate,
  TaskPublic,
  TaskType,
)
from app.service.post_service import PostService
from app.service.task_service import TaskService
from app.utils.instagram import extract_shortcode_from_url

STREAM_NAME = os.getenv("REDIS_STREAM", "tasks:instagram_download:stream")

REDIS_CHANNEL_OUTPUT = "tasks:instagram_download:output"

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskDownload(BaseModel):
  url: str


logger = logging.getLogger(__name__)


@router.post(
  "/",
  response_model=TaskPublic,
  status_code=status.HTTP_202_ACCEPTED,
)
async def create_task_download(
  *,
  request: Request,
  session: AsyncSessionDep,
  obj_in: CreateTaskDownload,
) -> TaskPublic:
  post_service = PostService(session=session)
  task_service = TaskService(session=session)

  try:
    task_id = uuid.uuid4()
    post_id = extract_shortcode_from_url(obj_in.url)

    if not post_id:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Invalid Instagram URL or shortcode not found.",
      )

    existing_post = await post_service.get_post_by_id(post_id=post_id)
    if existing_post:
      raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Post with id {post_id} already exists",
      )

    await post_service.create_post(post_id=post_id)

    task = await task_service.create_task(
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

    return task

  except ValueError as e:
    logger.error("ValueError while creating task: %s", e)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

  except HTTPException:
    raise

  except Exception as e:
    logger.exception("Unexpected error while creating task: %s", e)
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Internal server error",
    )


@router.get(
  "/{task_id}",
  response_model=TaskPublic,
  status_code=status.HTTP_200_OK,
)
async def get_task_by_id(
  *,
  session: AsyncSessionDep,
  task_id: str,
) -> TaskPublic:
  task_service = TaskService(session=session)

  try:
    _ = uuid.UUID(task_id)

  except ValueError:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"Invalid task_id: {task_id}",
    )

  try:
    task = await task_service.get_task_by_id(task_id=task_id)
    if not task:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id {task_id} not found",
      )
    return task

  except ValueError as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

  except HTTPException:
    raise

  except Exception as e:
    logger.exception("Unexpected error while fetching task %s: %s", task_id, e)
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Internal server error",
    )
