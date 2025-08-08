from typing import Optional
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.data.post import create_post, get_post_by_id, update_post
from app.schemas import PostPublic, PostUpdate


class PostService:
  """Service for post-related operations."""

  def __init__(
    self,
    session: AsyncSession,
  ):
    self.session = session

  async def create_post(
    self,
    post_id: str,
    user_id: UUID,
  ) -> None:
    """Create a new post."""

    _ = await create_post(
      session=self.session,
      post_id=post_id,
      user_id=user_id,
    )

  async def get_post_by_id(
    self,
    post_id: str,
    user_id: UUID,
  ) -> Optional[PostPublic]:
    """Get a post by its ID."""

    post = await get_post_by_id(
      session=self.session,
      post_id=post_id,
      user_id=user_id,
    )

    if post:
      return PostPublic.model_validate(post, from_attributes=True)

  async def update_post(
    self,
    post_id: str,
    user_id: UUID,
    post_update: PostUpdate,
  ) -> Optional[PostPublic]:
    """Update a post."""

    post = await update_post(
      session=self.session,
      post_id=post_id,
      user_id=user_id,
      post_update=post_update,
    )

    if post:
      return PostPublic.model_validate(post, from_attributes=True)
