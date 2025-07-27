from typing import Optional
from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.models import Post
from app.schemas import PostUpdate

T = Post
Statement = Select[T] | SelectOfScalar[T]


async def create_post(
  session: AsyncSession,
  post_id: str,
  user_id: UUID,
) -> Post:
  post = Post(
    id=post_id,
    user_id=user_id,
    author_id=None,
    description=None,
    taken_at=None,
  )

  session.add(post)
  await session.commit()
  await session.refresh(post)

  return post


async def get_post_by_id(
  session: AsyncSession,
  post_id: str,
  user_id: UUID,
) -> Optional[Post]:
  """
  Fetches a post by its ID, eagerly loading its images.

  This method uses `selectinload` to prevent lazy-loading issues
  during API response serialization. A # type: ignore is used to
  suppress a Pylance error, as the static type of Post.images
  (list[Image]) differs from the runtime type expected by selectinload.

  Args:
    post_id: The ID of the post to retrieve.

  Returns:
    The Post object with its relationships loaded, or None if not found.
  """

  stmt: Statement = (
    select(Post)
    .where(Post.id == post_id, Post.user_id == user_id)
    .options(selectinload(Post.images))  # type: ignore
  )
  result = await session.exec(stmt)
  post = result.one_or_none()

  return post


async def update_post(
  session: AsyncSession,
  post_id: str,
  user_id: UUID,
  post_update: PostUpdate,
) -> Optional[Post]:
  post = await get_post_by_id(
    session=session,
    post_id=post_id,
    user_id=user_id,
  )
  if not post:
    return None

  post_data = post_update.model_dump(exclude_unset=True)
  for key, value in post_data.items():
    setattr(post, key, value)

  session.add(post)
  await session.commit()
  await session.refresh(post)

  return post
