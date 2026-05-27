import os
from pathlib import Path

from fastapi.testclient import TestClient


TEST_DB_PATH = Path("/tmp/umkm_food_quality_auth_test.sqlite3")

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{TEST_DB_PATH}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("MODEL_PATH", "ml/model/exp_001_industry_biscuit_only/model.keras")
os.environ.setdefault("CLASS_INDICES_PATH", "ml/model/exp_001_industry_biscuit_only/class_indices.json")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from app.main import app  # noqa: E402


def test_auth_register_login_and_me_flow() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201
        assert register_response.json()["email"] == "test@example.com"

        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "test@example.com"


def test_register_duplicate_email_returns_409() -> None:
    with TestClient(app) as client:
        first_response = client.post(
            "/auth/register",
            json={
                "name": "Duplicate User One",
                "email": "duplicate@example.com",
                "password": "password123",
            },
        )
        assert first_response.status_code == 201

        second_response = client.post(
            "/auth/register",
            json={
                "name": "Duplicate User Two",
                "email": "duplicate@example.com",
                "password": "password123",
            },
        )
        assert second_response.status_code == 409
        assert second_response.json()["detail"] == "Email already registered"
