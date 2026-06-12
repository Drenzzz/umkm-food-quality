import json
import logging
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from app.core.config import get_settings


logger = logging.getLogger(__name__)


class EmailSender:
    def send(self, recipient: str, subject: str, body: str) -> None:
        raise NotImplementedError


class ConsoleEmailSender(EmailSender):
    def send(self, recipient: str, subject: str, body: str) -> None:
        logger.info("Email prepared for %s | %s | %s", recipient, subject, body)


class SMTPEmailSender(EmailSender):
    def send(self, recipient: str, subject: str, body: str) -> None:
        settings = get_settings()
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=10,
            ) as smtp:
                smtp.starttls()
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.exception("SMTP delivery failed for recipient=%s", recipient)
            raise RuntimeError(f"Email delivery failed: {exc}") from exc


class ResendEmailSender(EmailSender):
    """Sends mail through the Resend HTTPS API.

    Used on VPS providers that block outbound SMTP (e.g. DigitalOcean) but
    still allow HTTPS. The Resend free tier covers 100 emails/day which is
    enough for capstone demo traffic.
    """

    ENDPOINT = "https://api.resend.com/emails"

    def send(self, recipient: str, subject: str, body: str) -> None:
        settings = get_settings()
        if not settings.resend_api_key:
            raise RuntimeError("RESEND_API_KEY is not configured")

        payload = json.dumps(
            {
                "from": settings.email_from,
                "to": [recipient],
                "subject": subject,
                "text": body,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            self.ENDPOINT,
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "umkm-food-quality-api/1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status >= 400:
                    body_text = response.read().decode("utf-8", errors="replace")
                    logger.error(
                        "Resend API error status=%d body=%s",
                        response.status,
                        body_text,
                    )
                    raise RuntimeError(
                        f"Resend API returned status {response.status}: {body_text}"
                    )
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.exception("Resend delivery failed for recipient=%s", recipient)
            raise RuntimeError(f"Email delivery failed: {exc}") from exc


def get_email_sender() -> EmailSender:
    settings = get_settings()
    backend = settings.email_backend.lower()
    if backend == "smtp":
        return SMTPEmailSender()
    if backend == "resend":
        return ResendEmailSender()
    return ConsoleEmailSender()
