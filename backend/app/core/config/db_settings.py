import warnings
from typing import Self

from pydantic import computed_field, model_validator
from pydantic_core import MultiHostUrl

from app.core.config.base_config import BaseAppConfig


class DatabaseSettings(BaseAppConfig):
  POSTGRES_SERVER: str
  POSTGRES_PORT: int = 5432
  POSTGRES_USER: str
  POSTGRES_PASSWORD: str
  POSTGRES_DB: str

  @computed_field
  @property
  def SQLALCHEMY_DATABASE_URI(self) -> str:
    return str(
      MultiHostUrl.build(
        scheme="postgresql+psycopg",
        username=self.POSTGRES_USER,
        password=self.POSTGRES_PASSWORD,
        host=self.POSTGRES_SERVER,
        port=self.POSTGRES_PORT,
        path=self.POSTGRES_DB,
      )
    )

  @model_validator(mode="after")
  def _enforce_non_default_secrets(self) -> Self:
    if self.POSTGRES_PASSWORD == "changethis":
      msg = "POSTGRES_PASSWORD is set to default 'changethis'."

      if self.ENVIRONMENT == "local":
        warnings.warn(msg, stacklevel=1)

      else:
        raise ValueError(msg)

    return self
