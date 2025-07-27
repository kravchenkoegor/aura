from datetime import timedelta
from typing import Annotated

from fastapi import (
  APIRouter,
  Depends,
  HTTPException,
  Request,
  status,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AsyncSessionDep
from app.core import security
from app.core.config import settings
from app.core.rate_limit import (
  rate_limit_auth,
  rate_limit_password_recovery,
)
from app.core.security import get_password_hash
from app.data.user import (
  authenticate,
  get_user_by_email,
)
from app.schemas import (
  Message,
  NewPassword,
  Token,
)
from app.utils.email import (
  generate_reset_password_email,
  send_email,
)
from app.utils.reset_password import (
  generate_password_reset_token,
  verify_password_reset_token,
)

router = APIRouter(tags=["login"])


@router.post("/login", response_model=Token)
@rate_limit_auth
async def login_access_token(
  request: Request,
  session: AsyncSessionDep,
  form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> JSONResponse:
  """
  OAuth2 compatible token login, get an access token for future requests
  """

  user = await authenticate(
    session=session,
    email=form_data.username,
    password=form_data.password,
  )

  if not user:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Incorrect email or password",
    )

  elif not user.is_active:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Inactive user",
    )

  access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
  token_data = Token(
    access_token=security.create_access_token(
      user.id,
      expires_delta=access_token_expires,
    )
  )

  return JSONResponse(content=token_data.model_dump())


@router.post("/password-recovery/{email}")
@rate_limit_password_recovery
def recover_password(
  request: Request,
  session: AsyncSessionDep,
  email: str,
) -> Message:
  """
  Password Recovery
  """

  user = get_user_by_email(session=session, email=email)

  if not user:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="The user with this email does not exist in the system.",
    )

  password_reset_token = generate_password_reset_token(email=email)
  email_data = generate_reset_password_email(
    email_to=user.email,
    email=email,
    token=password_reset_token,
  )
  send_email(
    email_to=user.email,
    subject=email_data.subject,
    html_content=email_data.html_content,
  )

  return Message(message="Password recovery email sent")


@router.post("/reset-password/")
@rate_limit_auth
def reset_password(
  request: Request,
  session: AsyncSessionDep,
  body: NewPassword,
) -> Message:
  """
  Reset password
  """

  email = verify_password_reset_token(token=body.token)
  if not email:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid token",
    )

  user = get_user_by_email(session=session, email=email)
  if not user:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="The user with this email does not exist in the system.",
    )

  elif not user.is_active:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Inactive user",
    )

  hashed_password = get_password_hash(password=body.new_password)
  user.hashed_password = hashed_password
  session.add(user)
  session.commit()

  return Message(message="Password updated successfully")
