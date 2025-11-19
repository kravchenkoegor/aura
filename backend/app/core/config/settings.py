from typing import Optional, Self

from pydantic import HttpUrl, model_validator

from .ai_settings import AISettings
from .base_config import BaseAppConfig
from .cors_settings import CorsSettings
from .db_settings import DatabaseSettings
from .email_settings import EmailSettings
from .rate_limit_settings import RateLimitSettings
from .security_settings import SecuritySettings


class Settings(BaseAppConfig):
  """
  Main entry point for application settings.
  Composes the other settings classes.
  """

  PROJECT_NAME: str = "Aura App"
  SENTRY_DSN: Optional[HttpUrl] = None

  # Composition of sub-settings
  ai: AISettings = AISettings()
  cors: CorsSettings = CorsSettings()
  db: DatabaseSettings = DatabaseSettings()  # type: ignore[call-arg]
  email: EmailSettings = EmailSettings()
  rate_limit: RateLimitSettings = RateLimitSettings()
  security: SecuritySettings = SecuritySettings()  # type: ignore[call-arg]

  @model_validator(mode="after")
  def _apply_default_email_name(self) -> Self:
    """
    Cross-component logic: If email name isn't set, use Project Name.
    We do this here because EmailSettings doesn't know about PROJECT_NAME.
    """

    if not self.email.EMAILS_FROM_NAME:
      self.email.EMAILS_FROM_NAME = self.PROJECT_NAME

    return self


# Instantiate
settings = Settings()
