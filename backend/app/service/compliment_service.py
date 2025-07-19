import uuid

from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session

from app.data.image import get_primary_image_by_post_id
from app.models import Compliment
from app.schemas.compliment_output_schema import ComplimentOutput


class ComplimentService:
  def __init__(self, session: Session):
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

    def _create_compliments_sync() -> list[Compliment]:
      compliments = []

      for candidate in candidates:
        compliments.append(
          Compliment(
            image_id=image_id,
            # TODO: replace with actual language ID
            lang_id=uuid.UUID("923eebd0-4219-4574-8709-7d661cbbd0be"),
            generation_id=generation_metadata_id,
            text=candidate.comment.text,
            tone_breakdown=candidate.analysis.tone_breakdown.dict(),
          )
        )

      self.session.add_all(compliments)
      self.session.commit()

      # Refresh each created compliment to load DB-generated values like ID
      for compliment in compliments:
        self.session.refresh(compliment)

      return compliments

    return await run_in_threadpool(_create_compliments_sync)

  async def get_primary_image_by_post_id(
    self,
    post_id: str,
  ):
    """Fetches the primary image for a given post ID."""

    return await run_in_threadpool(
      get_primary_image_by_post_id,
      session=self.session,
      post_id=post_id,
    )
