from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from google import genai
from google.genai import types
from pydantic import ValidationError
from tenacity import (
  retry,
  stop_after_attempt,
  wait_exponential,
)

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

    self.client = genai.Client(api_key=settings.ai.GEMINI_API_KEY)
    self.model = settings.ai.GEMINI_MODEL

    self._system_prompt = self._get_system_prompt()

  def _get_system_prompt(self) -> str:
    """Get the system prompt from the configured file path."""
    system_prompt_path = Path("app/service/gemini_service/prompts/structured_json.md")

    if not system_prompt_path.exists():
      logger.error("System prompt file not found at %s", system_prompt_path)
      raise FileNotFoundError(
        f"System prompt file not found: {system_prompt_path}",
      )

    return system_prompt_path.read_text()

  @retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
  )
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

    logger.info("Sending request to Gemini API model: %s", self.model)

    response = await chat.send_message(
      message=[image_part, self._system_prompt],
      config=types.GenerateContentConfig(
        temperature=1.5,
        top_p=0.95,
        candidate_count=3,
        response_mime_type="application/json",
      ),
    )

    end_time = datetime.now()

    usage = response.usage_metadata

    prompt_tokens = (usage.prompt_token_count or 0) if usage else 0
    candidates_tokens = (usage.candidates_token_count or 0) if usage else 0
    total_tokens = (usage.total_token_count or 0) if usage else 0

    generation_metadata = GenerationMetadata(
      model_used=self.model or "unknown",
      prompt_token_count=prompt_tokens,
      candidates_token_count=candidates_tokens,
      total_token_count=total_tokens,
      analysis_duration_ms=int((end_time - start_time).total_seconds() * 1000),
    )

    self.session.add(generation_metadata)
    await self.session.commit()
    await self.session.refresh(generation_metadata)

    candidates: list[ComplimentOutput] = []

    if not response.candidates:
      logger.warning("Gemini returned no candidates. Check safety settings or prompt.")
      return (generation_metadata, [])

    for i, candidate in enumerate(response.candidates, 1):
      if candidate.content and candidate.content.parts:
        response_text = candidate.content.parts[0].text or ""

        try:
          validated_output = ComplimentOutput.model_validate_json(response_text)
          candidates.append(validated_output)

        except (json.JSONDecodeError, ValidationError) as e:
          logger.warning(
            "Invalid response format for candidate %s: %s",
            i,
            e,
            extra={"response_text": response_text},
          )
          continue
      else:
        logger.debug("Candidate %s has no content parts", i)

    return (generation_metadata, candidates)
