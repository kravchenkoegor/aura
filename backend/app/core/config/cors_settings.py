import warnings
from typing import Annotated, List, Self

from pydantic import (
  AnyUrl,
  BeforeValidator,
  computed_field,
  field_validator,
  model_validator,
)

from app.core.config.base_config import BaseAppConfig
from app.utils import parse_cors


class CorsSettings(BaseAppConfig):
  FRONTEND_HOST: str = "http://localhost:5173"
  BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = []

  CORS_ENABLED: bool = True

  CORS_ALLOW_CREDENTIALS: bool = True
  CORS_ALLOW_METHODS: List[str] = ["*"]
  CORS_ALLOW_HEADERS: List[str] = ["*"]
  CORS_EXPOSE_HEADERS: List[str] = []
  CORS_MAX_AGE: int = 600

  @field_validator("BACKEND_CORS_ORIGINS")
  @classmethod
  def validate_cors_origins(cls, v: list[AnyUrl] | str) -> list[str]:
    if isinstance(v, str):
      return [origin.strip() for origin in v.split(",") if origin.strip()]

    return [str(origin) for origin in v]

  @computed_field
  @property
  def all_cors_origins(self) -> list[str]:
    origins = []

    if isinstance(self.BACKEND_CORS_ORIGINS, list):
      origins.extend([str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS])

    frontend_normalized = self.FRONTEND_HOST.rstrip("/")
    if frontend_normalized not in origins:
      origins.append(frontend_normalized)

    return origins

  @model_validator(mode="after")
  def _validate_prod_cors(self) -> Self:
    if self.ENVIRONMENT == "production":
      if "*" in self.all_cors_origins:
        raise ValueError("Wildcard CORS (*) not allowed in production.")

      if not self.all_cors_origins:
        warnings.warn("No CORS origins configured for production.", stacklevel=1)

    return self
