import logging
import uuid

import httpx
from fastapi import (
  APIRouter,
  HTTPException,
  status,
)
from fastapi.responses import StreamingResponse

from app.api.deps import AsyncSessionDep
from app.service.image_service import ImageService

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{image_id}/view")
async def view_image_by_id(
  *,
  session: AsyncSessionDep,
  image_id: str,
):
  try:
    _ = uuid.UUID(image_id)

  except ValueError:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"Invalid image_id: {image_id}",
    )

  image_service = ImageService(session=session)

  image = await image_service.get_image_by_id(image_id=image_id)
  if not image:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

  url = image.storage_key

  try:

    async def stream_body():
      async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
          response.raise_for_status()

          async for chunk in response.aiter_bytes():
            yield chunk

    return StreamingResponse(
      stream_body(),
      media_type="image/jpeg",
      headers={
        "Access-Control-Allow-Origin": "*",
        "Cross-Origin-Resource-Policy": "cross-origin",
      },
    )

  except httpx.HTTPStatusError as e:
    logger.warning("Upstream image error: %s", e)

    raise HTTPException(
      status_code=e.response.status_code,
      detail="Upstream image not found or failed.",
    )

  except httpx.RequestError as e:
    logger.error("Request to upstream failed: %s", e)

    raise HTTPException(
      status_code=502,
      detail="Could not connect to the upstream server.",
    )

  except Exception as e:
    logger.exception(
      "Unexpected error while fetching image %s: %s",
      image_id,
      e,
    )

    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail="Internal server error",
    )
