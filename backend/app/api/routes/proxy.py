import logging
import uuid

import httpx
from fastapi import (
  APIRouter,
  HTTPException,
  Request,
  status,
)
from fastapi.responses import StreamingResponse

from app.api.deps import ImageServiceDep
from app.core.rate_limit import rate_limit_default

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/images", tags=["images"])


@router.get("/{image_id}/view")
@rate_limit_default
async def view_image_by_id(
  request: Request,
  *,
  image_service: ImageServiceDep,
  image_id: str,
):
  try:
    uuid.UUID(image_id)

  except ValueError:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"Invalid image_id: {image_id}",
    )

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
      status_code=status.HTTP_502_BAD_GATEWAY,
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
