import logging
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
  """
  Generate a unique key for rate limiting based on the configured strategy.

  Strategies:
    - "ip": Use client IP address only
    - "user": Use authenticated user ID only (falls back to IP if not authenticated)
    - "ip+user": Combine IP and user ID for stricter limiting

  Args:
    request: The incoming request

  Returns:
    A unique identifier string for rate limiting
  """

  strategy = settings.RATE_LIMIT_KEY_STRATEGY

  ip_address = get_remote_address(request)
  if ip_address in settings.RATE_LIMIT_EXEMPT_IPS:
    logger.debug("IP %s is exempt from rate limiting", ip_address)
    return f"exempt:{ip_address}"

  if strategy == "ip":
    return ip_address

  user_id = None
  if hasattr(request.state, "user") and request.state.user:
    user_id = str(request.state.user.id)

  if strategy == "user":
    return user_id if user_id else ip_address

  if strategy == "ip+user":
    if user_id:
      return f"{ip_address}:{user_id}"

    return ip_address

  return ip_address


def rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
  """
  Custom handler for rate limit exceeded errors.

  Args:
    request: The request that exceeded the rate limit
    exc: The rate limit exception

  Returns:
    JSON response with rate limit error details
  """

  logger.warning(
    "Rate limit exceeded for %s on %s %s",
    get_rate_limit_key(request),
    request.method,
    request.url.path,
  )

  return JSONResponse(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    content={
      "error": "rate_limit_exceeded",
      "message": "Too many requests. Please slow down and try again later.",
      "detail": str(exc),
    },
    headers={
      "Retry-After": "60",
    },
  )


limiter = Limiter(
  key_func=get_rate_limit_key,
  default_limits=[settings.RATE_LIMIT_DEFAULT] if settings.RATE_LIMIT_ENABLED else [],
  storage_uri=settings.rate_limit_storage_uri,
  headers_enabled=settings.RATE_LIMIT_HEADERS_ENABLED,
  swallow_errors=False,
)


def get_rate_limit_decorator(limit: str) -> Callable:
  """
  Get a rate limit decorator with the specified limit.

  Args:
    limit: Rate limit string (e.g., "5/minute", "100/hour")

  Returns:
    Decorator function for rate limiting
  """

  if not settings.RATE_LIMIT_ENABLED:

    def noop_decorator(func):
      return func

    return noop_decorator

  return limiter.limit(limit)


rate_limit_default = limiter.limit(settings.RATE_LIMIT_DEFAULT)
rate_limit_auth = limiter.limit(settings.RATE_LIMIT_AUTH)
rate_limit_password_recovery = limiter.limit(settings.RATE_LIMIT_PASSWORD_RECOVERY)
