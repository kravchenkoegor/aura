from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings


def _generate_token(email: str, expires_delta: timedelta, audience: str) -> str:
  """
  Generates a JWT with a specific expiry and audience.

  Args:
    email: The email address to encode in the token's 'sub' claim.
    expires_delta: The lifespan of the token.
    audience: The intended audience/purpose of the token (e.g., "password-reset").

  Returns:
      The encoded JWT as a string.
  """

  expire = datetime.now(timezone.utc) + expires_delta
  to_encode = {
    "exp": expire,
    "sub": str(email),
    "aud": audience,
  }

  encoded_jwt = jwt.encode(
    to_encode,
    settings.security.SECRET_KEY,
    algorithm=settings.security.JWT_ALGORITHM,
  )
  return encoded_jwt


def _verify_token(token: str, expected_audience: str) -> str | None:
  """
  Decodes a JWT, validates its audience, and returns the subject (email).

  Args:
    token: The JWT to decode.
    expected_audience: The audience the token must have.

  Returns:
    The email address (from 'sub' claim) if the token is valid, otherwise None.
  """

  try:
    payload = jwt.decode(
      token,
      settings.security.SECRET_KEY,
      algorithms=[settings.security.JWT_ALGORITHM],
      audience=expected_audience,
    )

    email: str | None = payload.get("sub")
    if email is None:
      return None

    return email

  except JWTError:
    return None


def generate_password_reset_token(email: str) -> str:
  """
  Generates a token for password reset.
  """

  delta = timedelta(minutes=settings.security.EMAIL_RESET_TOKEN_EXPIRE_MINUTES)
  return _generate_token(
    email=email,
    expires_delta=delta,
    audience="password-reset",
  )


def verify_password_reset_token(token: str) -> str | None:
  """
  Verifies the password reset token.
  Returns the user's email if the token is valid.
  """

  return _verify_token(
    token=token,
    expected_audience="password-reset",
  )


def generate_email_verify_token(email: str) -> str:
  """
  Generates a token for email verification.
  """

  delta = timedelta(hours=settings.security.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS)
  return _generate_token(
    email=email,
    expires_delta=delta,
    audience="email-verification",
  )


def verify_email_verify_token(token: str) -> str | None:
  """
  Verifies the email verification token.
  Returns the user's email if the token is valid.
  """

  return _verify_token(
    token=token,
    expected_audience="email-verification",
  )
