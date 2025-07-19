from app.data.language import create_languages
from app.data.user import create_user
from app.core.config import settings

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import User
from app.schemas import UserCreate

async_engine = create_async_engine(
  str(settings.SQLALCHEMY_DATABASE_URI),
  echo=True,
)

async_session = async_sessionmaker(
  async_engine,
  class_=AsyncSession,
  expire_on_commit=False,
)


async def init_db(session: AsyncSession) -> None:
  user_stmt = select(User).where(
    User.email == settings.FIRST_SUPERUSER
  )
  result = await session.exec(user_stmt)
  user = result.first()

  if not user:
    user_in = UserCreate(
      email=settings.FIRST_SUPERUSER,
      password=settings.FIRST_SUPERUSER_PASSWORD,
      is_superuser=True,
    )
    user = await create_user(session=session, user_create=user_in)

  await create_languages(session=session)
