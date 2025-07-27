from typing import List

from fastapi import (
  APIRouter,
  HTTPException,
  Request,
  status,
)

from app.api.deps import GeminiServiceDep, ImageServiceDep
from app.core.rate_limit import rate_limit_default
from app.schemas import ComplimentOutput, ComplimentRequest

router = APIRouter(prefix="/compliments", tags=["compliments"])


@router.post("/", response_model=List[ComplimentOutput])
@rate_limit_default
async def create_compliment(
  request: Request,
  *,
  gemini_service: GeminiServiceDep,
  image_service: ImageServiceDep,
  obj_in: ComplimentRequest,
) -> List[ComplimentOutput]:
  post_id = obj_in.post_id

  try:
    image = await image_service.get_primary_image_by_post_id(post_id)

    if not image:
      raise ValueError(f"No primary image found for post ID {post_id}")

    (generation_metadata, candidates) = await gemini_service.create_chat(
      session=session,
      post_id=post_id,
      style=obj_in.style,
    )

    # _ = await compliment_service.create_compliments(
    #   image_id=image_id,
    #   generation_metadata_id=generation_metadata.id,
    #   candidates=candidates,
    # )

    return candidates

  except ValueError as e:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=str(e),
    )

  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"An unexpected error occurred: {e}",
    )
