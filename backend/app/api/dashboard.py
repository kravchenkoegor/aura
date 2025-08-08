from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.deps import TaskServiceDep

router = APIRouter(
  prefix="/dashboard",
  tags=["dashboard"],
  include_in_schema=False,
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/tasks", response_class=HTMLResponse)
async def list_tasks(
  request: Request,
  task_service: TaskServiceDep,
  skip: int = Query(0, ge=0),
  limit: int = Query(20, ge=1, le=100),
):
  """List all tasks."""

  tasks = await task_service.get_all_tasks(skip=skip, limit=limit)

  return templates.TemplateResponse(
    request=request,
    name="tasks/list.html",
    context={
      "tasks": tasks,
      "skip": skip,
      "limit": limit,
    },
  )


@router.get("/tasks/{id}", response_class=HTMLResponse)
async def view_task(request: Request, id: str):
  """View a single task."""

  return templates.TemplateResponse(
    request=request,
    name="tasks/view_task.html",
    context={"id": id},
  )
