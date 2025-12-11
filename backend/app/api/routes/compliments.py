import os
import uuid
from typing import List

from fastapi import (
  APIRouter,
  HTTPException,
  Query,
  Request,
  status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import (
  ComplimentServiceDep,
  CurrentUser,
  TaskServiceDep,
)
from app.core.rate_limit import rate_limit_default
from app.schemas import (
  ComplimentPublic,
  ComplimentRequest,
  TaskCreate,
  TaskPublic,
  TaskType,
)

router = APIRouter(prefix="/compliments", tags=["compliments"])

STREAM_NAME = os.getenv(
  "REDIS_STREAM_COMPLIMENTS",
  "tasks:compliment_generation:stream",
)


@router.post(
  "/",
  response_model=TaskPublic,
  status_code=status.HTTP_202_ACCEPTED,
)
@rate_limit_default
async def create_compliment(
  request: Request,
  *,
  current_user: CurrentUser,
  task_service: TaskServiceDep,
  obj_in: ComplimentRequest,
) -> JSONResponse:
  """
  Create a new compliment generation task.
  """

  post_id = obj_in.post_id
  task_id = uuid.uuid4()

  try:
    task_data = await task_service.create_task(
      task_create=TaskCreate(
        id=task_id,
        type=TaskType.llm_generate,
        post_id=post_id,
        user_id=current_user.id,
      )
    )

    redis_client = request.app.state.redis_client
    await redis_client.xadd(
      STREAM_NAME,
      {
        "task_id": str(task_id),
        "post_id": post_id,
        "user_id": str(current_user.id),
      },
    )

    return JSONResponse(content=jsonable_encoder(task_data.model_dump()))

  except (SQLAlchemyError, RedisError) as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"An unexpected error occurred: {e}",
    )


@router.get(
  "/",
  response_model=List[ComplimentPublic],
  status_code=status.HTTP_200_OK,
)
@rate_limit_default
async def list_compliments(
  request: Request,
  *,
  current_user: CurrentUser,
  compliment_service: ComplimentServiceDep,
  skip: int = Query(
    0,
    ge=0,
    description="Number of compliments to skip",
  ),
  limit: int = Query(
    20,
    ge=1,
    le=100,
    description="Number of compliments to return",
  ),
) -> JSONResponse:
  """
  List all compliments for the current user.

  Superusers will see all compliments in the system.
  Regular users will only see their own compliments.
  """

  compliments_data = await compliment_service.get_all_compliments(
    skip=skip,
    limit=limit,
    user_id=(None if current_user.is_superuser else current_user.id),
  )

  compliments = [compliment.model_dump() for compliment in compliments_data]

  return JSONResponse(content=jsonable_encoder(compliments))
