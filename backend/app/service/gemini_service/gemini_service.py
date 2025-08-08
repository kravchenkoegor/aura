from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import settings
from app.models import GenerationMetadata
from app.schemas import ComplimentOutput

if TYPE_CHECKING:
  from app.api.deps import AsyncSessionDep

logger = logging.getLogger(__name__)


class GeminiService:
  """Service for interacting with the Gemini API."""

  def __init__(self, session: AsyncSessionDep):
    self.session = session
    self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    self.system_prompt = self._get_system_prompt()
    self.model = settings.GEMINI_MODEL

  def _get_system_prompt(self) -> str:
    """Get the system prompt from the configured file path."""

    if not settings.SYSTEM_PROMPT_PATH:
      raise ValueError("SYSTEM_PROMPT_PATH is not set")

    try:
      with open(settings.SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

    except FileNotFoundError:
      logger.error(f"System prompt file not found at {settings.SYSTEM_PROMPT_PATH}")
      raise

  async def create_chat(
    self,
    image_bytes: bytes,
  ) -> tuple[GenerationMetadata, list[ComplimentOutput]]:
    """Create a chat with the Gemini API and get compliments."""

    start_time = datetime.now()

    image_part = types.Part.from_bytes(
      data=image_bytes,
      mime_type="image/jpeg",
    )

    if not self.model:
      raise ValueError("GEMINI_MODEL is not set")

    chat = self.client.aio.chats.create(model=self.model)

    response = await chat.send_message(
      message=[image_part, self.system_prompt],
      config=types.GenerateContentConfig(
        temperature=1.5,
        top_p=0.95,
        candidate_count=3,
        response_mime_type="application/json",
      ),
    )

    end_time = datetime.now()

    usage = response.usage_metadata
    generation_metadata = GenerationMetadata(
      model_used=self.model or "unknown",
      prompt_token_count=usage.prompt_token_count if usage else 0,
      candidates_token_count=usage.candidates_token_count if usage else 0,
      total_token_count=usage.total_token_count if usage else 0,
      analysis_duration_ms=int((end_time - start_time).total_seconds() * 1000),
    )

    self.session.add(generation_metadata)
    await self.session.commit()
    await self.session.refresh(generation_metadata)

    candidates: list[ComplimentOutput] = []
    if response.candidates:
      for i, candidate in enumerate(response.candidates, 1):
        if candidate.content and candidate.content.parts:
          response_text = candidate.content.parts[0].text or ""

          try:
            validated_output = ComplimentOutput.model_validate_json(response_text)
            candidates.append(validated_output)

          except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
              f"Invalid response format for candidate {i}: {e}",
              extra={"response_text": response_text},
            )
            continue

    return (generation_metadata, candidates)
