import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.email import get_email_sender
from app.core.password_reset_token import (
    build_email_verification_expiration,
    build_email_verification_link,
    generate_password_reset_token,
    hash_password_reset_token,
)
from app.db.models import EmailVerification, User


logger = logging.getLogger(__name__)


class InvalidEmailVerificationTokenError(Exception):
    """Raised when email verification token is invalid, used, or expired."""


def send_email_verification(db: Session, user: User) -> None:
    if user.email_verified_at is not None:
        return

    db.execute(delete(EmailVerification).where(EmailVerification.user_id == user.id, EmailVerification.verified_at.is_(None)))

    raw_token = generate_password_reset_token()
    email_verification = EmailVerification(
        user_id=user.id,
        token_hash=hash_password_reset_token(raw_token),
        expires_at=build_email_verification_expiration(),
    )
    db.add(email_verification)
    db.commit()

    link = build_email_verification_link(raw_token)
    try:
        get_email_sender().send(
            recipient=user.email,
            subject="Verify your email",
            body=f"Use this link to verify your email: {link}",
        )
    except Exception:
        logger.exception("Email verification delivery failed for user_id=%s", user.id)


def verify_email_with_token(db: Session, token: str) -> User:
    token_hash = hash_password_reset_token(token)
    verification = db.scalar(select(EmailVerification).where(EmailVerification.token_hash == token_hash))

    if verification is None:
        raise InvalidEmailVerificationTokenError()

    now = datetime.now(UTC)
    expires_at = verification.expires_at if verification.expires_at.tzinfo else verification.expires_at.replace(tzinfo=UTC)
    if verification.verified_at is not None or expires_at < now:
        raise InvalidEmailVerificationTokenError()

    user = db.get(User, verification.user_id)
    if user is None:
        raise InvalidEmailVerificationTokenError()

    verification.verified_at = now
    user.email_verified_at = now
    db.commit()
    db.refresh(user)
    return user
