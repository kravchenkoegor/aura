import logging
import os
from typing import List
import uuid

from fastapi import (
  APIRouter,
  HTTPException,
  Query,
  Request,
  status,
)
from pydantic import BaseModel

from app.api.deps import (
  CurrentUser,
  PostServiceDep,
  TaskServiceDep,
)
from app.schemas import (
  TaskCreate,
  TaskPublic,
  TaskType,
)
from app.utils.instagram import extract_shortcode_from_url

STREAM_NAME = os.getenv("REDIS_STREAM", "tasks:instagram_download:stream")

REDIS_CHANNEL_OUTPUT = "tasks:instagram_download:output"

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskDownload(BaseModel):
  url: str


logger = logging.getLogger(__name__)


@router.post(
  "/download",
  response_model=TaskPublic,
  status_code=status.HTTP_202_ACCEPTED,
)
async def create_task_download(
  *,
  request: Request,
  current_user: CurrentUser,
  post_service: PostServiceDep,
  task_service: TaskServiceDep,
  obj_in: CreateTaskDownload,
) -> TaskPublic:
  """
  Create a new Instagram download task.

  Requires authentication. The task will be associated with the current user.
  """

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
        user_id=current_user.id,
      )
    )

    redis_client = request.app.state.redis_client
    await redis_client.xadd(
      STREAM_NAME,
      {
        "task_id": str(task_id),
        "url": obj_in.url,
        "user_id": str(current_user.id),
      },
    )

    logger.info(
      "Task %s created by user %s for post %s",
      task_id,
      current_user.id,
      post_id,
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
  current_user: CurrentUser,
  task_service: TaskServiceDep,
  task_id: str,
) -> TaskPublic:
  """
  Get a specific task by ID.

  Requires authentication. Users can only access their own tasks unless they are superusers.
  """

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

    if not current_user.is_superuser and task.user_id != current_user.id:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this task",
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


@router.get(
  "/",
  response_model=List[TaskPublic],
  status_code=status.HTTP_200_OK,
)
async def list_user_tasks(
  *,
  current_user: CurrentUser,
  task_service: TaskServiceDep,
  skip: int = Query(
    0,
    ge=0,
    description="Number of tasks to skip",
  ),
  limit: int = Query(
    20,
    ge=1,
    le=100,
    description="Number of tasks to return",
  ),
) -> List[TaskPublic]:
  """
  List all tasks for the current user.

  Superusers will see all tasks in the system.
  Regular users will only see their own tasks.
  """

  tasks = await task_service.get_all_tasks(
    skip=skip,
    limit=limit,
    user_id=(None if current_user.is_superuser else current_user.id),
  )

  return tasks
