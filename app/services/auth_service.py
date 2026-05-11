from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.schemas.auth import RegisterRequest


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.scalar(statement)


def create_user(db: Session, payload: RegisterRequest) -> User:
    existing_user = get_user_by_email(db, payload.email)
    if existing_user is not None:
        raise IntegrityError("Email already exists", params=None, orig=None)

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
    return user
