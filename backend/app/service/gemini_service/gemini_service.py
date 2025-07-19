import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool
from google import genai
from google.genai import types
from pydantic import ValidationError
from sqlmodel import Session, select

from app.models import (
  GenerationMetadata,
  Image,
  Post,
)
from app.schemas.compliment_output_schema import ComplimentOutput

load_dotenv()


class GeminiService:
  def __init__(self, session: Session):
    self.session = session

    self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    self.system_prompt = self._get_system_prompt()

    self.model = "gemini-2.5-flash"

  def _get_system_prompt(self) -> str:
    file_path = os.getenv("SYSTEM_PROMPT_PATH")
    if not file_path:
      raise FileNotFoundError("SYSTEM_PROMPT_PATH is not set")

    with open(file_path, "r", encoding="utf-8") as f:
      return f.read()

  async def create_chat(
    self,
    post_id: str,
    style: str,
  ):
    """Creates a new chat session with the specified model."""

    print("selected style:", style)

    def _sync_create_chat() -> tuple[GenerationMetadata, list[ComplimentOutput]]:
      start_time = datetime.now()

      chat = self.client.chats.create(
        model=self.model,
        config=types.GenerateContentConfig(
          temperature=1.5,
          top_p=0.95,
          candidate_count=3,
          response_mime_type="application/json",
        ),
      )

      existing_post = self.session.get(Post, post_id)

      if not existing_post:
        raise ValueError(f"Post with ID {post_id} not found")

      # Query for the primary image
      primary_image = self.session.exec(
        select(Image).where(
          Image.post_id == post_id,
          Image.is_primary,
        )
      ).first()

      if not primary_image:
        raise ValueError(f"Primary image for post {post_id} not found")

      image_bytes = requests.get(primary_image.storage_key).content
      image = types.Part.from_bytes(
        data=image_bytes,
        mime_type="image/jpeg",
      )

      response = chat.send_message(
        [
          image,
          self.system_prompt,
        ]
      )

      end_time = datetime.now()

      prompt_token_count = (
        response.usage_metadata.prompt_token_count if response.usage_metadata else 0
      )
      candidates_token_count = (
        response.usage_metadata.candidates_token_count if response.usage_metadata else 0
      )
      total_token_count = (
        response.usage_metadata.total_token_count if response.usage_metadata else 0
      )

      generation_metadata = GenerationMetadata(
        model_used=self.model,
        prompt_token_count=prompt_token_count or 0,
        candidates_token_count=candidates_token_count or 0,
        total_token_count=total_token_count or 0,
        analysis_duration_ms=int((end_time - start_time).total_seconds() * 1000),
      )

      self.session.add(generation_metadata)

      candidates: list[ComplimentOutput] = []

      if response.candidates and len(response.candidates) > 0:
        for i, candidate in enumerate(response.candidates, 1):
          if (
            candidate.content
            and candidate.content.parts
            and len(candidate.content.parts) > 0
          ):
            response_text = candidate.content.parts[0].text or ""

            try:
              # Parse and validate the JSON response
              response_data = json.loads(response_text)
              validated_output = ComplimentOutput(**response_data)
              candidates.append(validated_output)

            except (json.JSONDecodeError, ValidationError) as e:
              print(f"Invalid response format for candidate {i}: {e}")
              continue

      self.session.refresh(generation_metadata)

      return (generation_metadata, candidates)

    return await run_in_threadpool(_sync_create_chat)
