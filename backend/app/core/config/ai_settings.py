from typing import Optional

from app.core.config.base_config import BaseAppConfig


class AISettings(BaseAppConfig):
  GEMINI_API_KEY: Optional[str] = None
  GEMINI_MODEL: Optional[str] = "gemini-flash-latest"
