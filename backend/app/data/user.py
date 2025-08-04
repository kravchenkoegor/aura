from typing import Any, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models import User
from app.schemas import UserPublic, UserRegister, UserUpdate


async def create_user(
  *,
  session: AsyncSession,
  user_create: UserRegister,
) -> User:
  user_data = user_create.model_dump(exclude={"password"})
  hashed_password = get_password_hash(user_create.password)
  db_user = User(
    **user_data,
    hashed_password=hashed_password,
    is_active=False,
  )

  db_obj = User.model_validate(db_user)

  session.add(db_obj)
  await session.commit()
  await session.refresh(db_obj)

  return db_obj


async def update_user(
  *,
  session: AsyncSession,
  db_user: User,
  user_in: UserUpdate,
) -> Any:
  user_data = user_in.model_dump(exclude_unset=True)
  extra_data = {}

  if "password" in user_data:
    password = user_data["password"]
    hashed_password = get_password_hash(password)
    extra_data["hashed_password"] = hashed_password

  db_user.sqlmodel_update(user_data, update=extra_data)

  session.add(db_user)
  await session.commit()
  await session.refresh(db_user)

  return db_user


async def get_user_by_email(
  *,
  session: AsyncSession,
  email: str,
) -> Optional[User]:
  stmt = select(User).where(User.email == email)
  result = await session.exec(stmt)
  session_user = result.first()

  return session_user


async def authenticate(
  *,
  session: AsyncSession,
  email: str,
  password: str,
) -> Optional[UserPublic]:
  db_user = await get_user_by_email(session=session, email=email)

  if not db_user:
    return None

  if not verify_password(password, db_user.hashed_password):
    return None

  return UserPublic.model_validate(db_user)
