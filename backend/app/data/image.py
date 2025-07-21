from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Image


async def get_primary_image_by_post_id(
  session: AsyncSession,
  post_id: str,
) -> Optional[Image]:
  """Fetches the primary image for a given post ID."""

  stmt = select(Image).where(
    Image.post_id == post_id,
    Image.is_primary,
  )

  result = await session.exec(stmt)
  return result.first()


async def create_images(
  session: AsyncSession,
  images: List[Image],
) -> List[Image]:
  """Bulk insert image records into the database."""

  session.add_all(images)
  await session.commit()

  for image in images:
    await session.refresh(image)

  return images


async def get_image_by_id(
  session: AsyncSession,
  image_id: str,
) -> Optional[Image]:
  stmt = select(Image).where(Image.id == image_id)

  result = await session.exec(stmt)
  return result.one_or_none()
