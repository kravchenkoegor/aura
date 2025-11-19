from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError

from app.core import security
from app.core.config import settings


def generate_password_reset_token(email: str) -> str:
  """Generate a password reset token."""

  delta = timedelta(minutes=settings.security.EMAIL_RESET_TOKEN_EXPIRE_MINUTES)
  now = datetime.now(timezone.utc)
  expires = now + delta
  exp = expires.timestamp()

  encoded_jwt = jwt.encode(
    {
      "exp": exp,
      "nbf": now,
      "sub": email,
    },
    settings.security.SECRET_KEY,
    algorithm=security.ALGORITHM,
  )

  return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
  """Verify the password reset token."""

  try:
    decoded_token = jwt.decode(
      token,
      settings.security.SECRET_KEY,
      algorithms=[security.ALGORITHM],
    )

    return str(decoded_token["sub"])

  except InvalidTokenError:
    return None
