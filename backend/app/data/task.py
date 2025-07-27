from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Task
from app.schemas import TaskCreate, TaskStatus, TaskUpdate


async def create_task(session: AsyncSession, task_create: TaskCreate) -> Task:
  task = Task(
    id=task_create.id,
    type=task_create.type,
    post_id=task_create.post_id,
    image_id=task_create.image_id,
    user_id=task_create.user_id,
    status=TaskStatus.pending,
    created_at=datetime.now(timezone.utc),
  )

  session.add(task)
  await session.commit()
  await session.refresh(task)

  return task


async def get_task_by_id(session: AsyncSession, task_id: str) -> Optional[Task]:
  result = await session.exec(select(Task).where(Task.id == task_id))

  return result.first()


async def update_task(
  session: AsyncSession,
  task_id: str,
  task_update: TaskUpdate,
) -> Optional[Task]:
  task = await get_task_by_id(session, task_id)
  if not task:
    return None

  for key, value in task_update.model_dump(exclude_unset=True).items():
    setattr(task, key, value)

  task.updated_at = datetime.now(timezone.utc)

  session.add(task)
  await session.commit()
  await session.refresh(task)

  return task


async def set_task_status(
  session: AsyncSession,
  task_id: str,
  status: TaskStatus,
  duration: Optional[timedelta] = None,
) -> Optional[Task]:
  task = await get_task_by_id(session, task_id)
  if not task:
    return None

  task.status = status
  task.duration = duration
  task.updated_at = datetime.now(timezone.utc)

  session.add(task)
  await session.commit()
  await session.refresh(task)

  return task


async def get_all_tasks(
  session: AsyncSession,
  skip: int,
  limit: int,
  status: Optional[str] = None,
  user_id: Optional[UUID] = None,
) -> Sequence[Task]:
  query = select(Task).order_by(Task.created_at.desc())

  if status:
    query = query.where(Task.status == status)

  if user_id:
    query = query.where(Task.user_id == user_id)

  query = query.offset(skip).limit(limit)

  result = await session.exec(query)
  return result.all()
