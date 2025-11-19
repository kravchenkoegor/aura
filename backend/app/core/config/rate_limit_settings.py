import os
from typing import List, Literal, Optional

from pydantic import computed_field

from app.core.config.base_config import BaseAppConfig


class RateLimitSettings(BaseAppConfig):
  RATE_LIMIT_ENABLED: bool = True
  RATE_LIMIT_DEFAULT: str = "100/minute"
  RATE_LIMIT_AUTH: str = "5/minute"
  RATE_LIMIT_PASSWORD_RECOVERY: str = "3/hour"

  RATE_LIMIT_STORAGE_URL: Optional[str] = None
  RATE_LIMIT_HEADERS_ENABLED: bool = True
  RATE_LIMIT_KEY_STRATEGY: Literal["ip", "user", "ip+user"] = "ip"
  RATE_LIMIT_EXEMPT_IPS: List[str] = []

  @computed_field
  @property
  def storage_uri(self) -> str:
    """
    Get the storage URI for rate limiting.
    Falls back to Redis URL if not explicitly set.
    """

    if self.RATE_LIMIT_STORAGE_URL:
      return self.RATE_LIMIT_STORAGE_URL

    # Check environment directly for REDIS_URL as fallback
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
      return redis_url

    return "memory://"
