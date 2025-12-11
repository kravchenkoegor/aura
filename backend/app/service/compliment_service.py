import uuid
from typing import TYPE_CHECKING, Optional, Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Compliment, Image, Post
from app.schemas import ComplimentOutput, ComplimentPublic

if TYPE_CHECKING:
  from app.service.gemini_service import GeminiService


class ComplimentService:
  """Service for compliment-related operations."""

  def __init__(self, session: AsyncSession):
    self.session = session

  async def create_compliments(
    self,
    image_id: uuid.UUID,
    generation_metadata_id: uuid.UUID,
    candidates: list[ComplimentOutput],
  ) -> list[Compliment]:
    """Creates compliments for a given image based on the candidates provided.
    Args:
      image_id (uuid.UUID): The ID of the image for which compliments are being created.
      generation_metadata_id (uuid.UUID): The ID of the generation metadata associated with the compliments.
      candidates (list[ComplimentOutput]): A list of candidates containing the compliments and their analysis.
    Returns:
      list[Compliment]: A list of created Compliment objects with their IDs and other details.
    """

    compliments = []

    for _, candidate in enumerate(candidates, 1):
      compliment = Compliment(
        image_id=image_id,
        lang_id="en",
        generation_id=generation_metadata_id,
        text=candidate.comment.text,
        tone_breakdown=candidate.analysis.tone_breakdown.model_dump(),
      )

      compliments.append(compliment)

    self.session.add_all(compliments)
    await self.session.commit()

    for compliment in compliments:
      await self.session.refresh(compliment)

    return compliments

  async def get_all_compliments(
    self,
    skip: int,
    limit: int,
    user_id: Optional[uuid.UUID] = None,
  ) -> Sequence[ComplimentPublic]:
    """Get all compliments."""

    query = select(Compliment).join(Image).join(Post)

    if user_id:
      query = query.where(Post.user_id == user_id)

    query = query.offset(skip).limit(limit)

    result = await self.session.exec(query)
    compliments = result.all()

    return [
      ComplimentPublic.model_validate(compliment, from_attributes=True)
      for compliment in compliments
    ]

  async def get_compliment_by_id(
    self,
    compliment_id: uuid.UUID,
  ) -> Optional[Compliment]:
    """Get a compliment by ID."""

    return await self.session.get(Compliment, compliment_id)

  async def translate_compliment(
    self,
    compliment_id: uuid.UUID,
    target_language: str,
    gemini_service: "GeminiService",
  ) -> tuple[str, str]:
    """
    Translate a compliment to the target language.

    Args:
      compliment_id: The ID of the compliment to translate
      target_language: The target language code (e.g., 'tr' for Turkish)
      gemini_service: The Gemini service instance to use for translation

    Returns:
      A tuple of (original_text, translated_text)

    Raises:
      ValueError: If compliment is not found
    """

    compliment = await self.get_compliment_by_id(compliment_id)

    if not compliment:
      raise ValueError(f"Compliment with ID {compliment_id} not found")

    # Translate the compliment text
    translated_text = await gemini_service.translate(
      text=compliment.text,
      target_language=target_language,
    )

    return (compliment.text, translated_text)
