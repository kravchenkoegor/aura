import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class InstagramUrlRequest(BaseModel):
  """Schema for validating an Instagram URL."""

  url: str = Field(
    ...,
    description="Valid Instagram post URL (p/, reel/, tv/)",
    min_length=10,
    max_length=200,
    pattern=r"^https://(www\.|m\.|)instagram\.com/(p|reel|tv)/[A-Za-z0-9-_]+/?",
  )

  @field_validator("url")
  @classmethod
  def validate_instagram_url(cls, v: str) -> str:
    """Validate the Instagram URL."""

    parsed = urlparse(v)

    if parsed.scheme != "https":
      raise ValueError("URL must use HTTPS")

    if parsed.netloc not in {
      "instagram.com",
      "www.instagram.com",
      "m.instagram.com",
    }:
      raise ValueError("URL must be from instagram.com")

    if not re.search(r"/(p|reel|tv)/", v):
      raise ValueError("URL must point to a post, reel, or IGTV")

    return v
