from pydantic import EmailStr, computed_field

from app.core.config.base_config import BaseAppConfig


class EmailSettings(BaseAppConfig):
  SMTP_TLS: bool = True
  SMTP_SSL: bool = False
  SMTP_PORT: int = 587
  SMTP_HOST: str | None = None
  SMTP_USER: str | None = None
  SMTP_PASSWORD: str | None = None

  EMAILS_FROM_EMAIL: EmailStr | None = None
  EMAILS_FROM_NAME: str | None = None
  EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

  @computed_field
  @property
  def emails_enabled(self) -> bool:
    return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)
