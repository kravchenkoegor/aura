import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.routing import APIRoute
from redis.asyncio import Redis, from_url
from redis.exceptions import RedisError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.rate_limit import limiter, rate_limit_exceeded_handler

load_dotenv()

logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def custom_generate_unique_id(route: APIRoute) -> str:
  """Generate unique IDs for OpenAPI operations."""

  return f"{route.tags[0]}-{route.name}"


redis_client: Redis | None = None


def get_redis_client() -> Redis:
  """
  Get the initialized Redis client.

  Raises:
    RuntimeError: If Redis client was not initialized
  """

  if redis_client is None:
    raise RuntimeError("Redis client has not been initialized.")

  return redis_client


def validate_cors_configuration() -> None:
  """
  Validate CORS configuration on startup.

  Raises:
    ValueError: If critical CORS configuration issues are found
  """

  issues = []

  if settings.ENVIRONMENT == "production" and "*" in settings.all_cors_origins:
    issues.append(
      "CRITICAL: Wildcard (*) CORS origin detected in production environment."
    )

  if settings.ENVIRONMENT == "production":
    localhost_origins = [
      origin
      for origin in settings.all_cors_origins
      if "localhost" in origin or "127.0.0.1" in origin
    ]

    if localhost_origins:
      logger.warning("Localhost origins detected in production: %s", localhost_origins)

  if settings.ENVIRONMENT == "production":
    http_origins = [
      origin for origin in settings.all_cors_origins if origin.startswith("http://")
    ]

    if http_origins:
      logger.warning("Insecure HTTP origins detected in production: %s", http_origins)

  if issues:
    error_message = "\n".join(issues)
    raise ValueError(f"CORS Configuration Errors:\n{error_message}")


@asynccontextmanager
async def lifespan(app: FastAPI):
  """
  Manage application lifespan events.

  This replaces the deprecated @app.on_event("startup") and @app.on_event("shutdown")
  decorators with a single context manager.
  """

  logger.info("=" * 80)
  logger.info("Starting %s", settings.PROJECT_NAME)
  logger.info("Environment: %s", settings.ENVIRONMENT)
  logger.info("=" * 80)

  try:
    # Validate CORS configuration
    logger.info("Validating CORS configuration...")
    validate_cors_configuration()
    logger.info("✓ CORS configuration is valid")

    # Initialize Redis connection
    global redis_client
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
      raise ValueError("REDIS_URL environment variable is not set")

    logger.info("Connecting to Redis at %s...", redis_url)
    redis_client = from_url(redis_url, decode_responses=True)

    # Test Redis connection
    await redis_client.ping()

    app.state.redis_client = redis_client
    logger.info("✓ Redis connection established and verified")

    # Log CORS configuration details
    if settings.cors_enabled:
      logger.info("CORS Configuration:")
      logger.info("  Allowed Origins (%d):", len(settings.all_cors_origins))
      for origin in settings.all_cors_origins:
        logger.info("    • %s", origin)
      logger.info("  Allow Credentials: %s", settings.CORS_ALLOW_CREDENTIALS)
      logger.info("  Allow Methods: %s", settings.CORS_ALLOW_METHODS)
      logger.info("  Allow Headers: %s", settings.CORS_ALLOW_HEADERS)
      logger.info("  Max Age: %d seconds", settings.CORS_MAX_AGE)
    else:
      logger.warning("⚠ CORS is disabled")

    # Log API documentation URLs
    logger.info("API Documentation:")
    logger.info("  OpenAPI Spec: /openapi.json")
    logger.info("  Swagger UI: /docs")
    logger.info("  ReDoc: /redoc")

    logger.info("=" * 80)
    logger.info("✓ Application startup complete - Ready to accept requests")
    logger.info("=" * 80)

  except (ValueError, RedisError) as e:
    logger.error("=" * 80)
    logger.error("✗ Application startup failed!")
    logger.error("Error: %s", str(e))
    logger.error("=" * 80)
    raise

  yield

  logger.info("=" * 80)
  logger.info("Shutting down %s", settings.PROJECT_NAME)
  logger.info("=" * 80)

  try:
    # Close Redis connection gracefully
    if redis_client:
      await redis_client.close()
      logger.info("✓ Redis connection closed successfully")

    logger.info("=" * 80)
    logger.info("✓ Application shutdown complete")
    logger.info("=" * 80)

  except RedisError as e:
    logger.error("Error during shutdown: %s", str(e))


# Initialize FastAPI application
app = FastAPI(
  title=settings.PROJECT_NAME,
  openapi_url="/openapi.json",
  generate_unique_id_function=custom_generate_unique_id,
  lifespan=lifespan,
  description=(f"{settings.PROJECT_NAME} API - Environment: {settings.ENVIRONMENT}"),
  version="1.0.0",
  docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
  redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

app.state.limiter = limiter

if settings.RATE_LIMIT_ENABLED:
  app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
  app.add_middleware(SlowAPIMiddleware)
  logger.info("✓ Rate limiting middleware enabled")

# Configure CORS middleware
if settings.cors_enabled:
  app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=settings.CORS_EXPOSE_HEADERS,
    max_age=settings.CORS_MAX_AGE,
  )

# Add trusted host middleware for production
if settings.ENVIRONMENT == "production":
  allowed_hosts = []
  for origin in settings.all_cors_origins:
    if "://" in origin:
      host = origin.split("://")[1].split("/")[0].split(":")[0]
      allowed_hosts.append(host)

  if allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

app.include_router(api_router)
