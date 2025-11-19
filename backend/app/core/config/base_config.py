from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppConfig(BaseSettings):
  """Base config that others inherit from to share env_file settings."""

  model_config = SettingsConfigDict(
    env_file=".env",
    env_ignore_empty=True,
    extra="ignore",
  )

  # We need ENVIRONMENT in multiple classes for validation logic
  ENVIRONMENT: Literal["local", "staging", "production"] = "local"
