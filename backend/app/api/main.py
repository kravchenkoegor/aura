from fastapi import APIRouter

from app.api.dashboard import router as dashboard_router
from app.api.routes import (
  compliments,
  login,
  posts,
  proxy,
  tasks,
  utils,
)
from app.api.websockets import router as websocket_router

api_router = APIRouter()

api_router.include_router(login.router)
api_router.include_router(utils.router)

api_router.include_router(compliments.router)
api_router.include_router(posts.router)
api_router.include_router(proxy.router)
api_router.include_router(tasks.router)

api_router.include_router(websocket_router)

api_router.include_router(dashboard_router)
