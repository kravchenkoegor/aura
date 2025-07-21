from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import AsyncSessionDep
from app.schemas import ComplimentOutput
from app.service.gemini_service import GeminiService
from app.service.image_service import ImageService

router = APIRouter(prefix="/compliments", tags=["compliments"])


class ComplimentRequest(BaseModel):
  post_id: str
  style: str


@router.post("/", response_model=List[ComplimentOutput])
async def create_compliment(
  *,
  session: AsyncSessionDep,
  obj_in: ComplimentRequest,
) -> List[ComplimentOutput]:
  gemini_service = GeminiService(session=session)
  image_service = ImageService(session=session)

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
    raise HTTPException(status_code=400, detail=str(e))

  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"An unexpected error occurred: {e}",
    )
