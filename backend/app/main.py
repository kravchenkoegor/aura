# import sentry_sdk
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.routing import APIRoute
from redis.asyncio import Redis, from_url
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings

load_dotenv()


def custom_generate_unique_id(route: APIRoute) -> str:
  return f"{route.tags[0]}-{route.name}"


redis_client: Redis | None = None


def get_redis_client() -> Redis:
  """
  Функция-зависимость для получения уже созданного клиента Redis.
  """

  if redis_client is None:
    # Этого не должно произойти в контексте работающего приложения FastAPI
    raise RuntimeError("Redis клиент не был инициализирован.")

  return redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
  # Initialize Redis client
  global redis_client
  redis_url = os.getenv("REDIS_URL")
  if not redis_url:
    raise ValueError("REDIS_URL не задан в переменных окружения")

  print("Подключение к Redis...")
  # Создаем клиент один раз
  redis_client = from_url(redis_url, decode_responses=True)

  app.state.redis_client = redis_client

  print("Application startup: Redis listener initialized.")

  yield  # Application is running

  # Clean up on shutdown
  await redis_client.close()
  print("Application shutdown: Redis client closed.")


# if settings.SENTRY_DSN and settings.ENVIRONMENT != 'local':
#   sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
  title=settings.PROJECT_NAME,
  openapi_url="/openapi.json",
  generate_unique_id_function=custom_generate_unique_id,
  lifespan=lifespan,
)

# Set all CORS enabled origins
if settings.all_cors_origins:
  app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

app.include_router(api_router)
