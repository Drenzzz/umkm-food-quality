from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.db.models import Detection, EmailVerification, PasswordReset, User
from app.schemas.auth import ChangePasswordRequest, DeleteAccountRequest, RegisterRequest, UpdateProfileRequest


class EmailAlreadyExistsError(Exception):
    """Raised when registration is attempted with an email that already exists."""


class InvalidCurrentPasswordError(Exception):
    """Raised when the current password does not match the stored password."""


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def create_user(db: Session, payload: RegisterRequest) -> User:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise EmailAlreadyExistsError(payload.email)

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    settings = get_settings()
    if settings.require_verified_email and user.email_verified_at is None:
        return None
    return user


def update_user_profile(db: Session, user: User, payload: UpdateProfileRequest) -> User:
    if not verify_password(payload.current_password, user.password_hash):
        raise InvalidCurrentPasswordError()

    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None and existing_user.id != user.id:
        raise EmailAlreadyExistsError(payload.email)

    email_changed = user.email != str(payload.email)
    user.name = payload.name
    user.email = str(payload.email)

    # Revoke verification when email changes — new address must be verified again
    if email_changed:
        user.email_verified_at = None

    db.commit()
    db.refresh(user)

    if email_changed:
        from app.services.email_verification_service import send_email_verification
        send_email_verification(db, user)

    return user


def change_user_password(db: Session, user: User, payload: ChangePasswordRequest) -> User:
    if not verify_password(payload.current_password, user.password_hash):
        raise InvalidCurrentPasswordError()

    user.password_hash = hash_password(payload.new_password)
    user.last_password_change_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def delete_user_account(db: Session, user: User, payload: DeleteAccountRequest) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise InvalidCurrentPasswordError()

    db.execute(delete(EmailVerification).where(EmailVerification.user_id == user.id))
    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
    db.execute(delete(Detection).where(Detection.user_id == user.id))
    db.delete(user)
    db.commit()
