from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.email import get_email_sender
from app.core.password_reset_token import (
    build_password_reset_expiration,
    build_password_reset_link,
    generate_password_reset_token,
    hash_password_reset_token,
)
from app.core.security import hash_password
from app.db.models import PasswordReset, User
from app.services.auth_service import get_user_by_email


class InvalidPasswordResetTokenError(Exception):
    """Raised when password reset token is invalid, used, or expired."""


def request_password_reset(db: Session, email: str) -> None:
    user = get_user_by_email(db, email)
    if user is None:
        return

    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None)))

    raw_token = generate_password_reset_token()
    password_reset = PasswordReset(
        user_id=user.id,
        token_hash=hash_password_reset_token(raw_token),
        expires_at=build_password_reset_expiration(),
    )
    db.add(password_reset)
    db.commit()

    link = build_password_reset_link(raw_token)
    get_email_sender().send(
        recipient=user.email,
        subject="Reset your password",
        body=f"Use this link to reset your password: {link}",
    )


def reset_password_with_token(db: Session, token: str, new_password: str) -> User:
    token_hash = hash_password_reset_token(token)
    statement = select(PasswordReset).where(PasswordReset.token_hash == token_hash)
    password_reset = db.scalar(statement)

    if password_reset is None:
        raise InvalidPasswordResetTokenError()

    now = datetime.now(UTC)
    expires_at = password_reset.expires_at if password_reset.expires_at.tzinfo else password_reset.expires_at.replace(tzinfo=UTC)
    if password_reset.used_at is not None or expires_at < now:
        raise InvalidPasswordResetTokenError()

    user = db.get(User, password_reset.user_id)
    if user is None:
        raise InvalidPasswordResetTokenError()

    user.password_hash = hash_password(new_password)
    user.last_password_change_at = now
    password_reset.used_at = now
    db.commit()
    db.refresh(user)
    return user
