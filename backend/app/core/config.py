import os
import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
  AnyUrl,
  BeforeValidator,
  EmailStr,
  HttpUrl,
  PostgresDsn,
  computed_field,
  field_validator,
  model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
  """Parse CORS origins from comma-separated string or list."""
  if isinstance(v, str) and not v.startswith("["):
    return [i.strip() for i in v.split(",")]
  elif isinstance(v, list | str):
    return v
  raise ValueError(v)


class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file=".env",
    env_ignore_empty=True,
    extra="ignore",
  )

  SECRET_KEY: str = secrets.token_urlsafe(32)
  JWT_ALGORITHM: str = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 1

  # Token expiration times
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
  EMAIL_RESET_TOKEN_EXPIRE_MINUTES: int = 30
  EMAIL_VERIFY_TOKEN_EXPIRE_HOURS: int = 24

  FRONTEND_HOST: str = "http://localhost:5173"
  ENVIRONMENT: Literal["local", "staging", "production"] = "local"

  # CORS Configuration
  BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

  # Additional CORS settings for fine-grained control
  CORS_ALLOW_CREDENTIALS: bool = True
  CORS_ALLOW_METHODS: list[str] = ["*"]
  CORS_ALLOW_HEADERS: list[str] = ["*"]
  CORS_EXPOSE_HEADERS: list[str] = []
  CORS_MAX_AGE: int = 600  # 10 minutes

  # Rate limit configuration
  RATE_LIMIT_ENABLED: bool = True
  RATE_LIMIT_DEFAULT: str = "100/minute"
  RATE_LIMIT_AUTH: str = "5/minute"
  RATE_LIMIT_PASSWORD_RECOVERY: str = "3/hour"

  RATE_LIMIT_STORAGE_URL: str | None = None
  RATE_LIMIT_HEADERS_ENABLED: bool = True
  RATE_LIMIT_KEY_STRATEGY: Literal["ip", "user", "ip+user"] = "ip"
  RATE_LIMIT_EXEMPT_IPS: list[str] = []

  @field_validator("BACKEND_CORS_ORIGINS")
  @classmethod
  def validate_cors_origins(cls, v: list[AnyUrl] | str) -> list[str]:
    """Validate and normalize CORS origins."""

    if isinstance(v, str):
      return [origin.strip() for origin in v.split(",") if origin.strip()]

    return [str(origin) for origin in v]

  @computed_field
  @property
  def all_cors_origins(self) -> list[str]:
    """
    Combine all CORS origins from multiple sources.

    Returns:
      List of normalized CORS origin URLs (without trailing slashes)
    """

    origins = []

    # Add explicitly configured backend origins
    if isinstance(self.BACKEND_CORS_ORIGINS, list):
      origins.extend([str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS])

    # Add frontend host if not already included
    frontend_normalized = self.FRONTEND_HOST.rstrip("/")
    if frontend_normalized not in origins:
      origins.append(frontend_normalized)

    return origins

  @computed_field
  @property
  def cors_enabled(self) -> bool:
    """Check if CORS should be enabled based on configuration."""

    return len(self.all_cors_origins) > 0

  @computed_field  # type: ignore[prop-decorator]
  @property
  def rate_limit_storage_uri(self) -> str:
    """
    Get the storage URI for rate limiting.
    Falls back to Redis URL if not explicitly set.
    """

    if self.RATE_LIMIT_STORAGE_URL:
      return self.RATE_LIMIT_STORAGE_URL

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
      return redis_url

    # Fall back to in-memory (not recommended for production)
    return "memory://"

  PROJECT_NAME: str
  SENTRY_DSN: HttpUrl | None = None

  # Database Configuration
  POSTGRES_SERVER: str
  POSTGRES_PORT: int = 5432
  POSTGRES_USER: str
  POSTGRES_PASSWORD: str = ""
  POSTGRES_DB: str = ""

  @computed_field  # type: ignore[prop-decorator]
  @property
  def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
    return MultiHostUrl.build(
      scheme="postgresql+psycopg",
      username=self.POSTGRES_USER,
      password=self.POSTGRES_PASSWORD,
      host=self.POSTGRES_SERVER,
      port=self.POSTGRES_PORT,
      path=self.POSTGRES_DB,
    )

  # Email Configuration
  SMTP_TLS: bool = True
  SMTP_SSL: bool = False
  SMTP_PORT: int = 587
  SMTP_HOST: str | None = None
  SMTP_USER: str | None = None
  SMTP_PASSWORD: str | None = None
  EMAILS_FROM_EMAIL: EmailStr | None = None
  EMAILS_FROM_NAME: str | None = None

  @model_validator(mode="after")
  def _set_default_emails_from(self) -> Self:
    if not self.EMAILS_FROM_NAME:
      self.EMAILS_FROM_NAME = self.PROJECT_NAME
    return self

  EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

  @computed_field  # type: ignore[prop-decorator]
  @property
  def emails_enabled(self) -> bool:
    return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

  # User Configuration
  EMAIL_TEST_USER: EmailStr = "test@example.com"
  FIRST_SUPERUSER: EmailStr
  FIRST_SUPERUSER_PASSWORD: str

  def _check_default_secret(self, var_name: str, value: str | None) -> None:
    """Validate that secrets are not using default values in production."""

    if value == "changethis":
      message = (
        f'The value of {var_name} is "changethis", '
        "for security, please change it, at least for deployments."
      )

      if self.ENVIRONMENT == "local":
        warnings.warn(message, stacklevel=1)

      else:
        raise ValueError(message)

  @model_validator(mode="after")
  def _enforce_non_default_secrets(self) -> Self:
    """Enforce non-default secrets for production environments."""

    self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
    self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
    self._check_default_secret(
      "FIRST_SUPERUSER_PASSWORD",
      self.FIRST_SUPERUSER_PASSWORD,
    )

    return self

  @model_validator(mode="after")
  def _validate_cors_configuration(self) -> Self:
    """Validate CORS configuration for security."""

    if self.ENVIRONMENT == "production":
      # In production, wildcard CORS should never be allowed
      if "*" in self.all_cors_origins:
        raise ValueError(
          "Wildcard CORS origins (*) are not allowed in production. "
          "Please specify explicit origins in BACKEND_CORS_ORIGINS."
        )

      # Warn if no CORS origins are configured in production
      if not self.all_cors_origins:
        warnings.warn(
          "No CORS origins configured for production environment. "
          "This may cause frontend connectivity issues.",
          stacklevel=1,
        )

    return self


settings = Settings()  # type: ignore
