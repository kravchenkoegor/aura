from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
  """Response schema for image upload."""

  post_id: str = Field(..., description="Generated post ID for the uploaded image")
  image_id: str = Field(..., description="Generated image ID")
  message: str = Field(default="Image uploaded successfully")


class ImageUploadRequest(BaseModel):
  """Request schema for image upload metadata."""

  style: str = Field(
    default="romantic",
    pattern=r"^(romantic|poetic|flirtatious|witty|curious|casual|playful)$",
    description="Style of compliment to generate",
  )
