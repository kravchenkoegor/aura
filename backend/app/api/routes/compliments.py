from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import AsyncSessionDep
from app.schemas import ComplimentPublic
from app.service.compliment_service import ComplimentService
from app.service.gemini_service.gemini_service import GeminiService

router = APIRouter(prefix="/compliments", tags=["compliments"])


class ComplimentRequest(BaseModel):
  post_id: str
  style: str


@router.post("/", response_model=list[ComplimentPublic])
async def create_compliment(
  *,
  session: AsyncSessionDep,
  obj_in: ComplimentRequest,
) -> Any:
  compliment_service = ComplimentService(session=session)
  gemini_service = GeminiService(session=session)

  post_id = obj_in.post_id

  try:
    image_id = await compliment_service.get_primary_image_by_post_id(post_id)

    if not image_id:
      raise ValueError(f"No primary image found for post ID {post_id}")

    (generation_metadata, candidates) = await gemini_service.create_chat(
      post_id=post_id,
      style=obj_in.style,
    )

    _ = await compliment_service.create_compliments(
      image_id=image_id,
      generation_metadata_id=generation_metadata.id,
      candidates=candidates,
    )

    return candidates

  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
