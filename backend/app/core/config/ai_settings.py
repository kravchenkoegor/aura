from typing import Literal, Optional

from app.core.config.base_config import BaseAppConfig


class AISettings(BaseAppConfig):
  # LLM Provider selection
  LLM_PROVIDER: Literal["GEMINI", "LLAMA"] = "GEMINI"

  # Instagram Scraper backend selection
  INSTAGRAM_SCRAPER: Literal["INSTALOADER", "PLAYWRIGHT"] = "INSTALOADER"

  # Gemini settings
  GEMINI_API_KEY: Optional[str] = None
  GEMINI_MODEL: Optional[str] = "gemini-flash-latest"

  # Llama.cpp settings
  LLAMA_SERVER_URL: Optional[str] = "http://localhost:8080"
  LLAMA_MODEL: Optional[str] = "llama-vision"
