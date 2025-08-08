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
from pydantic import BaseModel

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
  create_user,
  get_user_by_email,
)
from app.schemas import (
  ForgotPassword,
  Message,
  NewPassword,
  Token,
  UserRegister,
)
from app.utils.email import (
  generate_reset_password_email,
  generate_verification_email,
  send_email,
)
from app.utils.tokens import (
  generate_email_verify_token,
  generate_password_reset_token,
  verify_email_verify_token,
  verify_password_reset_token,
)


class TokenPayload(BaseModel):
  token: str


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/sign-up", response_model=Message)
@rate_limit_auth
async def sign_up(
  request: Request,
  session: AsyncSessionDep,
  user_in: UserRegister,
) -> JSONResponse:
  """
  Create a new user.
  A verification email will be sent to the user's email address.
  """

  user = await get_user_by_email(session=session, email=user_in.email)
  if user:
    raise HTTPException(
      status_code=status.HTTP_409_CONFLICT,
      detail="The user with this email already exists in the system.",
    )

  user = await create_user(
    session=session,
    user_create=user_in,
  )

  verification_token = generate_email_verify_token(email=user_in.email)
  email_data = generate_verification_email(
    email_to=user.email,
    email=user.email,
    token=verification_token,
  )
  send_email(
    email_to=user.email,
    subject=email_data.subject,
    html_content=email_data.html_content,
  )

  message_data = Message(
    message="Please check your email to verify your account.",
  )

  return JSONResponse(content=message_data.model_dump())


@router.post("/verify-email", response_model=Message)
@rate_limit_auth
async def verify_email(
  request: Request,
  session: AsyncSessionDep,
  obj_in: TokenPayload,
) -> JSONResponse:
  """
  Verify a user's email address with the provided token.
  """

  email = verify_email_verify_token(token=obj_in.token)
  if not email:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid or expired token",
    )

  user = await get_user_by_email(session=session, email=email)
  if not user:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="The user with this email does not exist in the system.",
    )

  if user.is_active:
    message_data = Message(message="Account already verified.")

    return JSONResponse(content=message_data.model_dump())

  user.is_active = True
  session.add(user)
  await session.commit()

  message_data = Message(
    message="Email verified successfully. You can now sign in.",
  )

  return JSONResponse(content=message_data.model_dump())


@router.post("/sign-in", response_model=Token)
@rate_limit_auth
async def sign_in(
  request: Request,
  session: AsyncSessionDep,
  form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> JSONResponse:
  """
  OAuth2 compatible token login, get an access token for future requests.
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
      detail="Inactive user. Please verify your email first.",
    )

  access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
  token_data = Token(
    token=security.create_access_token(
      user.id,
      expires_delta=access_token_expires,
    )
  )

  return JSONResponse(content=token_data.model_dump())


@router.post("/forgot-password", response_model=Message)
@rate_limit_password_recovery
async def forgot_password(  # Renamed and made async
  request: Request,
  session: AsyncSessionDep,
  obj_in: ForgotPassword,
) -> JSONResponse:
  """
  Password Recovery. Sends an email with a reset token.
  """

  email = obj_in.email
  user = await get_user_by_email(session=session, email=email)

  if not user:
    # To prevent email enumeration, we can return a success message
    # even if the user does not exist.
    # However, for development/clarity, raising an error is also fine.
    # Let's stick to the original logic for now.
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

  message_data = Message(message="Password recovery email sent")

  return JSONResponse(content=message_data.model_dump())


@router.post("/reset-password", response_model=Message)
@rate_limit_auth
async def reset_password(
  request: Request,
  session: AsyncSessionDep,
  obj_in: NewPassword,
) -> JSONResponse:
  """
  Reset password using the token from the recovery email.
  """

  email = verify_password_reset_token(token=obj_in.token)
  if not email:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Invalid or expired token",
    )

  user = await get_user_by_email(session=session, email=email)
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

  hashed_password = get_password_hash(password=obj_in.new_password)
  user.hashed_password = hashed_password

  session.add(user)
  await session.commit()

  message_data = Message(message="Password updated successfully")

  return JSONResponse(content=message_data.model_dump())
