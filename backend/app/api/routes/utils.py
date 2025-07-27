from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic.networks import EmailStr

from app.api.deps import get_current_active_superuser
from app.schemas import Message
from app.utils.email import generate_test_email, send_email

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
  "/test-email/",
  dependencies=[Depends(get_current_active_superuser)],
  status_code=status.HTTP_201_CREATED,
  response_model=Message,
)
def test_email(email_to: EmailStr) -> JSONResponse:
  """
  Test emails.
  """
  email_data = generate_test_email(email_to=email_to)
  send_email(
    email_to=email_to,
    subject=email_data.subject,
    html_content=email_data.html_content,
  )

  message_data = Message(message="Test email sent")

  return JSONResponse(content=message_data.model_dump())


@router.get("/health-check/")
async def health_check() -> bool:
  return True
