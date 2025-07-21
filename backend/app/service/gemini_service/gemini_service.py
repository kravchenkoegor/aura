import json
import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import ValidationError
from sqlmodel import select

from app.api.deps import AsyncSessionDep
from app.models import (
  GenerationMetadata,
  Image,
  Post,
)
from app.schemas import ComplimentOutput

load_dotenv()


class GeminiService:
  def __init__(self, session: AsyncSessionDep):
    self.session = session

    self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    self.system_prompt = self._get_system_prompt()

    self.model = "gemini-2.5-flash"

  def _get_system_prompt(self) -> str:
    print(os.getcwd())
    # file_path = os.getenv("SYSTEM_PROMPT_PATH")
    file_path = os.path.join(
      os.getcwd(),
      "app/service/gemini_service/prompts/structured_json.md",
    )
    if not file_path:
      raise FileNotFoundError("SYSTEM_PROMPT_PATH is not set")

    with open(file_path, "r", encoding="utf-8") as f:
      return f.read()

  async def create_chat(
    self,
    session: AsyncSessionDep,
    post_id: str,
    style: str,
  ) -> tuple[GenerationMetadata, list[ComplimentOutput]]:
    start_time = datetime.now()

    existing_post = await session.get(Post, post_id)
    if not existing_post:
      raise ValueError(f"Post with ID {post_id} not found")

    result = await session.exec(
      select(Image).where(
        Image.post_id == post_id,
        Image.is_primary,
      ),
    )
    primary_image = result.first()

    if not primary_image:
      raise ValueError(f"Primary image for post {post_id} not found")

    async with httpx.AsyncClient() as client:
      http_response = await client.get(primary_image.storage_key)
      http_response.raise_for_status()
      image_bytes = http_response.content

    image_part = types.Part.from_bytes(
      data=image_bytes,
      mime_type="image/jpeg",
    )

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
      model_used=self.model,
      prompt_token_count=usage.prompt_token_count if usage else 0,
      candidates_token_count=usage.candidates_token_count if usage else 0,
      total_token_count=usage.total_token_count if usage else 0,
      analysis_duration_ms=int((end_time - start_time).total_seconds() * 1000),
    )

    session.add(generation_metadata)
    await session.commit()
    await session.refresh(generation_metadata)

    candidates: list[ComplimentOutput] = []
    if response.candidates:
      for i, candidate in enumerate(response.candidates, 1):
        if candidate.content and candidate.content.parts:
          response_text = candidate.content.parts[0].text or ""
          try:
            validated_output = ComplimentOutput.model_validate_json(
              response_text,
            )
            candidates.append(validated_output)
          except (json.JSONDecodeError, ValidationError) as e:
            # Рекомендуется использовать логгер вместо print
            print(f"Invalid response format for candidate {i}: {e}")
            continue

    return (generation_metadata, candidates)
