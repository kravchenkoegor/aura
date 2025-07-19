import uuid
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Author


async def create_author(
  session: AsyncSession,
  username: str,
) -> Optional[uuid.UUID]:
  author = Author(
    id=uuid.uuid4(),
    username=username,
  )

  session.add(author)
  await session.commit()
  await session.refresh(author)

  return author.id


async def get_author_by_id(
  session: AsyncSession,
  author_id: str,
) -> Optional[uuid.UUID]:
  # TODO: username можно сменить, убрать ключ
  stmt = select(Author.id).where(Author.username == author_id)
  result = await session.exec(stmt)

  return result.first()
