from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Language


async def create_languages(session: AsyncSession):
  """Create the languages in the database."""

  stmt = (
    insert(Language)
    .values(
      [
        {"id": "en", "name": "English"},
        {"id": "tr", "name": "Türkçe"},
      ]
    )
    .on_conflict_do_nothing(index_elements=["id"])
  )

  await session.execute(stmt)
  await session.commit()
