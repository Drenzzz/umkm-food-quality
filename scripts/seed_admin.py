"""
Seed an admin user by promoting an existing user or creating a new one.

Usage:
    # Promote existing user to admin
    python scripts/seed_admin.py user@example.com

    # Create new admin user
    python scripts/seed_admin.py user@example.com --create --name "Admin Name" --password "Password123"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.security import hash_password
from app.db.models import User


def load_database_url() -> str:
    from app.core.config import get_settings

    return get_settings().database_url


def promote_user(db: Session, email: str) -> bool:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        return False

    if user.role == "admin":
        print(f"  User '{email}' is already an admin.")
        return True

    user.role = "admin"
    db.commit()
    print(f"  Promoted '{email}' to admin.")
    return True


def create_admin(db: Session, email: str, name: str, password: str) -> bool:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        print(f"  User '{email}' already exists (role: {existing.role}).")
        return False

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role="admin",
    )
    db.add(user)
    db.commit()
    print(f"  Created admin user '{email}'.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed an admin user.")
    parser.add_argument("email", help="Email of the user to promote or create.")
    parser.add_argument("--create", action="store_true", help="Create a new user instead of promoting.")
    parser.add_argument("--name", default="Admin", help="Name for new user (only with --create).")
    parser.add_argument("--password", default="Admin123", help="Password for new user (only with --create).")
    args = parser.parse_args()

    database_url = load_database_url()
    # Ensure psycopg3 dialect is used (backend uses psycopg, not psycopg2)
    if database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
    engine = create_engine(database_url)

    with Session(engine) as db:
        if args.create:
            success = create_admin(db, args.email, args.name, args.password)
        else:
            success = promote_user(db, args.email)

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
