import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Compliment
from app.schemas import ComplimentOutput


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

    for i, candidate in enumerate(candidates, 1):
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
