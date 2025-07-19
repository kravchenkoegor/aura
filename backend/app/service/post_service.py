from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from app.data.post import create_post, get_post_by_id, update_post
from app.schemas import PostPublic, PostUpdate


class PostService:
  def __init__(
    self,
    session: AsyncSession,
  ):
    self.session = session

  async def create_post(self, post_id: str) -> None:
    _ = await create_post(
      session=self.session,
      post_id=post_id,
    )

  async def get_post_by_id(self, post_id: str) -> Optional[PostPublic]:
    post = await get_post_by_id(
      session=self.session,
      post_id=post_id,
    )

    if post:
      return PostPublic.model_validate(post, from_attributes=True)

  async def update_post(
    self,
    post_id: str,
    post_update: PostUpdate,
  ) -> Optional[PostPublic]:
    post = await update_post(
      session=self.session,
      post_id=post_id,
      post_update=post_update,
    )

    if post:
      return PostPublic.model_validate(post, from_attributes=True)
