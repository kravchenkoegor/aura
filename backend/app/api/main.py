from fastapi import APIRouter

from app.api.routes import (
  compliments,
  login,
  private,
  proxy,
  posts,
  tasks,
  utils,
)
from app.api.websockets import router as websocket_router
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(utils.router)

api_router.include_router(compliments.router)
api_router.include_router(posts.router)
api_router.include_router(proxy.router)
api_router.include_router(tasks.router)

api_router.include_router(websocket_router)

if settings.ENVIRONMENT == "local":
  api_router.include_router(private.router)
