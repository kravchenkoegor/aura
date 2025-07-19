from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from app.data import task as task_repo
from app.models import Task
from app.schemas import TaskCreate, TaskPublic, TaskStatus, TaskUpdate


class TaskService:
  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_task(self, task_create: TaskCreate) -> TaskPublic:
    task = await task_repo.create_task(
      session=self.session,
      task_create=task_create,
    )

    return TaskPublic.model_validate(task, from_attributes=True)

  async def get_task_by_id(self, task_id: str) -> Optional[TaskPublic]:
    task = await task_repo.get_task_by_id(
      session=self.session,
      task_id=task_id,
    )

    if task:
      return TaskPublic.model_validate(task, from_attributes=True)

  async def update_task(
    self,
    task_id: str,
    task_update: TaskUpdate,
  ) -> Optional[Task]:
    return await task_repo.update_task(
      session=self.session,
      task_id=task_id,
      task_update=task_update,
    )

  async def set_status(
    self,
    task_id: str,
    status: TaskStatus,
  ) -> Optional[Task]:
    return await task_repo.set_task_status(
      session=self.session,
      task_id=task_id,
      status=status,
    )
