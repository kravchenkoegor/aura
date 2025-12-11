import base64
import io
import os
import uuid
from typing import List

from fastapi import (
  APIRouter,
  File,
  Form,
  HTTPException,
  Query,
  Request,
  UploadFile,
  status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from PIL import Image as PILImage
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import (
  AsyncSessionDep,
  ComplimentServiceDep,
  CurrentUser,
  GeminiServiceDep,
  PostServiceDep,
  TaskServiceDep,
)
from app.core.rate_limit import rate_limit_default
from app.data.image import create_images
from app.models import Image
from app.schemas import (
  ComplimentPublic,
  ComplimentRequest,
  ImageUploadResponse,
  TaskCreate,
  TaskPublic,
  TaskType,
  TranslateRequest,
  TranslateResponse,
)

router = APIRouter(prefix="/compliments", tags=["compliments"])

STREAM_NAME = os.getenv(
  "REDIS_STREAM_COMPLIMENTS",
  "tasks:compliment_generation:stream",
)


@router.post(
  "/",
  response_model=TaskPublic,
  status_code=status.HTTP_202_ACCEPTED,
)
@rate_limit_default
async def create_compliment(
  request: Request,
  *,
  current_user: CurrentUser,
  task_service: TaskServiceDep,
  obj_in: ComplimentRequest,
) -> JSONResponse:
  """
  Create a new compliment generation task.
  """

  post_id = obj_in.post_id
  task_id = uuid.uuid4()

  try:
    task_data = await task_service.create_task(
      task_create=TaskCreate(
        id=task_id,
        type=TaskType.llm_generate,
        post_id=post_id,
        user_id=current_user.id,
      )
    )

    redis_client = request.app.state.redis_client
    await redis_client.xadd(
      STREAM_NAME,
      {
        "task_id": str(task_id),
        "post_id": post_id,
        "user_id": str(current_user.id),
      },
    )

    return JSONResponse(content=jsonable_encoder(task_data.model_dump()))

  except (SQLAlchemyError, RedisError) as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"An unexpected error occurred: {e}",
    )


@router.post(
  "/upload",
  response_model=TaskPublic,
  status_code=status.HTTP_202_ACCEPTED,
)
@rate_limit_default
async def upload_image(
  request: Request,
  session: AsyncSessionDep,
  *,
  current_user: CurrentUser,
  post_service: PostServiceDep,
  task_service: TaskServiceDep,
  file: UploadFile = File(...),
  style: str = Form(
    default="romantic",
    pattern=r"^(romantic|poetic|flirtatious|witty|curious|casual|playful)$",
  ),
) -> JSONResponse:
  """
  Upload an image directly and create a compliment generation task.

  This endpoint accepts direct image uploads (jpg, jpeg, png) and creates
  a synthetic post record for compliment generation.

  Args:
    file: The image file to upload (max 10MB, jpg/jpeg/png only)
    style: The style of compliment to generate (default: romantic)

  Returns:
    Task information for polling the compliment generation status
  """

  # Validate file format
  if not file.content_type or not file.content_type.startswith("image/"):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="File must be an image",
    )

  allowed_formats = ["image/jpeg", "image/jpg", "image/png"]
  if file.content_type not in allowed_formats:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"Image format not supported. Allowed formats: jpg, jpeg, png. Got: {file.content_type}",
    )

  # Read file content
  file_content = await file.read()

  # Validate file size (10MB limit)
  max_size = 10 * 1024 * 1024  # 10MB in bytes
  if len(file_content) > max_size:
    raise HTTPException(
      status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
      detail=f"File size exceeds maximum allowed size of 10MB. File size: {len(file_content) / 1024 / 1024:.2f}MB",
    )

  # Validate it's a valid image and get dimensions
  try:
    image = PILImage.open(io.BytesIO(file_content))
    width, height = image.size

    # Verify it's actually a valid image
    image.verify()

    # Re-open after verify (verify closes the file)
    image = PILImage.open(io.BytesIO(file_content))

  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail=f"Invalid image file: {str(e)}",
    )

  # Generate a unique post_id for the upload
  post_id = f"upload_{uuid.uuid4().hex[:11]}"
  task_id = uuid.uuid4()

  try:
    # Create a synthetic post record
    await post_service.create_post(
      post_id=post_id,
      user_id=current_user.id,
    )

    # Convert image to base64 data URL for storage
    # For uploaded images, we'll store them as base64 data URLs
    mime_type = file.content_type
    base64_data = base64.b64encode(file_content).decode("utf-8")
    storage_key = f"data:{mime_type};base64,{base64_data}"

    # Create image record
    image_record = Image(
      post_id=post_id,
      storage_key=storage_key,
      height=height,
      width=width,
      is_primary=True,
    )

    # Save the image record to the database
    await create_images(
      session=session,
      images=[image_record],
    )

    # Create task for compliment generation
    task_data = await task_service.create_task(
      task_create=TaskCreate(
        id=task_id,
        type=TaskType.llm_generate,
        post_id=post_id,
        user_id=current_user.id,
      )
    )

    # Add to Redis stream for worker processing
    redis_client = request.app.state.redis_client
    await redis_client.xadd(
      STREAM_NAME,
      {
        "task_id": str(task_id),
        "post_id": post_id,
        "user_id": str(current_user.id),
      },
    )

    return JSONResponse(content=jsonable_encoder(task_data.model_dump()))

  except (SQLAlchemyError, RedisError) as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"An unexpected error occurred: {e}",
    )


@router.get(
  "/",
  response_model=List[ComplimentPublic],
  status_code=status.HTTP_200_OK,
)
@rate_limit_default
async def list_compliments(
  request: Request,
  *,
  current_user: CurrentUser,
  compliment_service: ComplimentServiceDep,
  skip: int = Query(
    0,
    ge=0,
    description="Number of compliments to skip",
  ),
  limit: int = Query(
    20,
    ge=1,
    le=100,
    description="Number of compliments to return",
  ),
) -> JSONResponse:
  """
  List all compliments for the current user.

  Superusers will see all compliments in the system.
  Regular users will only see their own compliments.
  """

  compliments_data = await compliment_service.get_all_compliments(
    skip=skip,
    limit=limit,
    user_id=(None if current_user.is_superuser else current_user.id),
  )

  compliments = [compliment.model_dump() for compliment in compliments_data]

  return JSONResponse(content=jsonable_encoder(compliments))


@router.post(
  "/{compliment_id}/translate",
  response_model=TranslateResponse,
  status_code=status.HTTP_200_OK,
)
@rate_limit_default
async def translate_compliment(
  request: Request,
  *,
  compliment_id: uuid.UUID,
  current_user: CurrentUser,
  compliment_service: ComplimentServiceDep,
  gemini_service: GeminiServiceDep,
  obj_in: TranslateRequest,
) -> JSONResponse:
  """
  Translate a compliment to the target language.

  Args:
    compliment_id: The UUID of the compliment to translate
    obj_in: Translation request containing target language

  Returns:
    Translation response with original and translated text
  """

  try:
    # Get the compliment first to check if it exists
    compliment = await compliment_service.get_compliment_by_id(compliment_id)

    if not compliment:
      raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Compliment with ID {compliment_id} not found",
      )

    # Translate the compliment
    original_text, translated_text = await compliment_service.translate_compliment(
      compliment_id=compliment_id,
      target_language=obj_in.target_language,
      gemini_service=gemini_service,
    )

    # Prepare response
    response_data = TranslateResponse(
      compliment_id=compliment_id,
      original_text=original_text,
      original_language=compliment.lang_id,
      translated_text=translated_text,
      target_language=obj_in.target_language,
    )

    return JSONResponse(content=jsonable_encoder(response_data.model_dump()))

  except ValueError as e:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=str(e),
    )
  except Exception as e:
    raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"Translation failed: {str(e)}",
    )
