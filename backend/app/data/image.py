from typing import List, Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Image, Post


async def get_primary_image_by_post_id(
  session: AsyncSession,
  post_id: str,
  user_id: UUID,
) -> Optional[Image]:
  """Fetches the primary image for a given post ID."""

  stmt = (
    select(Image)
    .join(Post)
    .where(
      Image.post_id == post_id,
      Image.is_primary,
      Post.user_id == user_id,
    )
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
  """Get an image by its ID."""

  stmt = select(Image).where(Image.id == image_id)

  result = await session.exec(stmt)
  return result.one_or_none()
