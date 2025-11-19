import secrets
import warnings
from typing import Self

from pydantic import EmailStr, model_validator

from app.core.config.base_config import BaseAppConfig


class SecuritySettings(BaseAppConfig):
  SECRET_KEY: str = secrets.token_urlsafe(32)
  JWT_ALGORITHM: str = "HS256"

  # Tokens
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
  EMAIL_RESET_TOKEN_EXPIRE_MINUTES: int = 30
  EMAIL_VERIFY_TOKEN_EXPIRE_HOURS: int = 24

  # Superuser
  FIRST_SUPERUSER: EmailStr
  FIRST_SUPERUSER_PASSWORD: str
  EMAIL_TEST_USER: EmailStr = "test@example.com"

  @model_validator(mode="after")
  def _enforce_non_default_secrets(self) -> Self:
    checks = [
      ("SECRET_KEY", self.SECRET_KEY),
      ("FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD),
    ]

    for name, value in checks:
      if value == "changethis":
        msg = f"{name} is set to default 'changethis'."

        if self.ENVIRONMENT == "local":
          warnings.warn(msg, stacklevel=1)

        else:
          raise ValueError(msg)

    return self
