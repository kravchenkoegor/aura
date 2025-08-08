from sqlalchemy.ext.asyncio import (
  async_sessionmaker,
  create_async_engine,
)
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.data.language import create_languages
from app.models import User

async_engine = create_async_engine(
  str(settings.SQLALCHEMY_DATABASE_URI),
  echo=False,
)

async_session = async_sessionmaker(
  async_engine,
  class_=AsyncSession,
  expire_on_commit=False,
)


async def init_db(session: AsyncSession) -> None:
  """Initializes the database with necessary data."""

  user_stmt = select(User).where(User.email == settings.FIRST_SUPERUSER)
  result = await session.exec(user_stmt)
  user = result.first()

  if not user:
    hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
    user = User(
      email=settings.FIRST_SUPERUSER,
      hashed_password=hashed_password,
      is_superuser=True,
      is_active=True,
    )

    session.add(user)
    await session.commit()

  await create_languages(session=session)
