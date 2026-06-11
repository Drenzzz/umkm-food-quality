import logging
import smtplib
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


def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.email_backend.lower() == "smtp":
        return SMTPEmailSender()
    return ConsoleEmailSender()
