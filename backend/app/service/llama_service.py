from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
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


class LlamaService:
  """Service for interacting with Llama.cpp server."""

  def __init__(self, session: AsyncSessionDep):
    self.session = session
    self.server_url = settings.ai.LLAMA_SERVER_URL or "http://localhost:8080"
    self.model = settings.ai.LLAMA_MODEL or "llama-vision"
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
    """Create a chat with the Llama.cpp server and get compliments."""

    start_time = datetime.now()

    # Convert image bytes to base64
    base64_image_data = base64.b64encode(image_bytes).decode("utf-8")

    # Prepare the messages in OpenAI-compatible format
    messages = [
      {
        "role": "system",
        "content": self._system_prompt,
      },
      {
        "role": "user",
        "content": [
          {
            "type": "image_url",
            "image_url": {
              "url": f"data:image/jpeg;base64,{base64_image_data}",
            },
          },
        ],
      },
    ]

    # Request configuration
    request_payload = {
      "messages": messages,
      "stream": False,
      "temperature": 1.5,
      "top_p": 0.95,
      "n_predict": 2048,
      "n": 3,  # Generate 3 candidates
    }

    logger.info("Sending request to Llama.cpp server at %s", self.server_url)

    async with httpx.AsyncClient(timeout=120.0) as client:
      try:
        response = await client.post(
          f"{self.server_url}/v1/chat/completions",
          json=request_payload,
          headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

      except httpx.HTTPStatusError as e:
        logger.error(
          "HTTP error from Llama.cpp server: %s - %s",
          e.response.status_code,
          e.response.text,
        )
        raise
      except httpx.RequestError as e:
        logger.error("Request error to Llama.cpp server: %s", str(e))
        raise

    end_time = datetime.now()

    # Validate response structure
    if "choices" not in data:
      logger.error("Invalid response format from Llama.cpp server: %s", data)
      raise ValueError("Invalid response format from LLM server")

    # Extract usage metadata if available
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", 0)

    generation_metadata = GenerationMetadata(
      model_used=self.model,
      prompt_token_count=prompt_tokens,
      candidates_token_count=completion_tokens,
      total_token_count=total_tokens,
      analysis_duration_ms=int((end_time - start_time).total_seconds() * 1000),
    )

    self.session.add(generation_metadata)
    await self.session.commit()
    await self.session.refresh(generation_metadata)

    candidates: list[ComplimentOutput] = []

    if not data.get("choices"):
      logger.warning("Llama.cpp returned no choices. Check server configuration.")
      return (generation_metadata, [])

    for i, choice in enumerate(data["choices"], 1):
      if "message" in choice and "content" in choice["message"]:
        response_text = choice["message"]["content"]

        try:
          # Parse the JSON response and validate against schema
          validated_output = ComplimentOutput.model_validate_json(response_text)
          candidates.append(validated_output)

        except (json.JSONDecodeError, ValidationError) as e:
          logger.warning(
            "Invalid response format for choice %s: %s",
            i,
            e,
            extra={"response_text": response_text},
          )
          continue
      else:
        logger.debug("Choice %s has no content", i)

    return (generation_metadata, candidates)
