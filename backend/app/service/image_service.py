from typing import Optional
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.data.image import (
  get_image_by_id,
  get_primary_image_by_post_id,
)
from app.schemas import ImagePublic


class ImageService:
  def __init__(
    self,
    session: AsyncSession,
  ):
    self.session = session

  async def get_image_by_id(
    self,
    image_id: str,
  ) -> Optional[ImagePublic]:
    image = await get_image_by_id(
      session=self.session,
      image_id=image_id,
    )

    if image:
      return ImagePublic.model_validate(image, from_attributes=True)

  async def get_primary_image_by_post_id(
    self,
    post_id: str,
    user_id: UUID,
  ) -> Optional[ImagePublic]:
    image = await get_primary_image_by_post_id(
      session=self.session,
      post_id=post_id,
      user_id=user_id,
    )

    if image:
      return ImagePublic.model_validate(image, from_attributes=True)
