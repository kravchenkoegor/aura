from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.models import Image


async def get_primary_image_by_post_id(
  session: AsyncSession,
  post_id: str,
) -> Optional[UUID]:
  '''Fetches the primary image for a given post ID.'''

  stmt = select(Image.id).where(
    Image.post_id == post_id,
    Image.is_primary,
  )

  result = await session.exec(stmt)
  return result.first()


async def create_images(
  session: AsyncSession,
  images: List[Image],
) -> List[Image]:
  '''Bulk insert image records into the database.'''

  session.add_all(images)
  await session.commit()

  for image in images:
    await session.refresh(image)

  return images
