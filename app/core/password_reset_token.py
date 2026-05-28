from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from app.core.config import get_settings


def generate_password_reset_token() -> str:
    return token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def build_password_reset_expiration() -> datetime:
    settings = get_settings()
    return datetime.now(UTC) + timedelta(minutes=settings.password_reset_token_ttl_minutes)


def build_password_reset_link(token: str) -> str:
    settings = get_settings()
    separator = "&" if "?" in settings.reset_password_frontend_url else "?"
    return f"{settings.reset_password_frontend_url}{separator}token={token}"


def build_email_verification_expiration() -> datetime:
    settings = get_settings()
    return datetime.now(UTC) + timedelta(minutes=settings.email_verification_token_ttl_minutes)


def build_email_verification_link(token: str) -> str:
    settings = get_settings()
    separator = "&" if "?" in settings.verify_email_frontend_url else "?"
    return f"{settings.verify_email_frontend_url}{separator}token={token}"
