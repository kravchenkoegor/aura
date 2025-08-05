import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import emails
from jinja2 import Template

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
  html_content: str
  subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
  """
  Reads and renders a Jinja2 email template from the filesystem.
  """

  template_path = (
    Path(__file__).parent.parent / "email-templates" / "build" / template_name
  )
  try:
    template_str = template_path.read_text()

  except FileNotFoundError:
    logger.error(f"Could not find email template: {template_path}")

    return f"Error: Email template '{template_name}' not found."

  html_content = Template(template_str).render(context)

  return html_content


def send_email(
  *,
  email_to: str,
  subject: str = "",
  html_content: str = "",
) -> None:
  """
  Sends an email using the 'emails' library and SMTP settings.
  """

  if not settings.emails_enabled:
    logger.warning("Email sending is disabled. Skipping send_email call.")

    return

  message = emails.Message(
    subject=subject,
    html=html_content,
    mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
  )

  smtp_options = {
    "host": settings.SMTP_HOST,
    "port": settings.SMTP_PORT,
  }
  if settings.SMTP_TLS:
    smtp_options["tls"] = True

  elif settings.SMTP_SSL:
    smtp_options["ssl"] = True

  if settings.SMTP_USER:
    smtp_options["user"] = settings.SMTP_USER

  if settings.SMTP_PASSWORD:
    smtp_options["password"] = settings.SMTP_PASSWORD

  try:
    response = message.send(to=email_to, smtp=smtp_options)
    logger.info(f"Send email result: {response.status_code} {response.status_text}")

  except Exception as e:
    logger.error(f"Failed to send email to {email_to}: {e}")


def generate_verification_email(email_to: str, email: str, token: str) -> EmailData:
  """
  Generates the email content for account verification.
  """

  project_name = settings.PROJECT_NAME
  subject = f"{project_name} - Verify your account"
  link = f"{settings.FRONTEND_HOST}/verify-email?token={token}"

  html_content = render_email_template(
    template_name="verify-email.html",
    context={
      "project_name": project_name,
      "username": email,
      "email": email_to,
      "valid_hours": settings.EMAIL_VERIFY_TOKEN_EXPIRE_HOURS,
      "link": link,
    },
  )

  return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(
  email_to: str,
  email: str,
  token: str,
) -> EmailData:
  """
  Generates the email content for password recovery.
  """

  project_name = settings.PROJECT_NAME
  subject = f"{project_name} - Password recovery for user {email}"
  link = f"{settings.FRONTEND_HOST}/reset-password?token={token}"

  html_content = render_email_template(
    template_name="reset_password.html",
    context={
      "project_name": project_name,
      "username": email,
      "email": email_to,
      "valid_minutes": settings.EMAIL_RESET_TOKEN_EXPIRE_MINUTES,
      "link": link,
    },
  )

  return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
  email_to: str,
  username: str,
  password: str,
) -> EmailData:
  """
  Generates the email for an admin-created new account.

  SECURITY WARNING: Sending passwords in plaintext via email is highly discouraged.
  This function should only be used in trusted, internal admin flows.
  A better practice is to send a password reset link instead.
  """

  project_name = settings.PROJECT_NAME
  subject = f"{project_name} - Your new account"

  html_content = render_email_template(
    template_name="new_account.html",
    context={
      "project_name": project_name,
      "username": username,
      "password": password,
      "email": email_to,
      "link": settings.FRONTEND_HOST,
    },
  )

  return EmailData(html_content=html_content, subject=subject)


def generate_test_email(email_to: str) -> EmailData:
  """
  Generates a test email for debugging SMTP configuration.
  """

  project_name = settings.PROJECT_NAME
  subject = f"{project_name} - Test email"
  html_content = render_email_template(
    template_name="test_email.html",
    context={
      "project_name": settings.PROJECT_NAME,
      "email": email_to,
    },
  )

  return EmailData(html_content=html_content, subject=subject)
