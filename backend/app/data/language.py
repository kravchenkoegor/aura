from app.models import Language
from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession


async def create_languages(session: AsyncSession):
  stmt = insert(Language).values([
    {"id": "en", "name": "English"},
    {"id": "tr", "name": "Türkçe"},
  ]).on_conflict_do_nothing(index_elements=["id"])

  await session.execute(stmt)
  await session.commit()
