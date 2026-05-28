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


def test_update_profile_with_current_password() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Profile User",
                "email": "profile@example.com",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "profile@example.com",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        update_response = client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Updated Profile User",
                "email": "profile-updated@example.com",
                "current_password": "password123",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Profile User"
        assert update_response.json()["email"] == "profile-updated@example.com"


def test_update_profile_rejects_wrong_current_password() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Wrong Password User",
                "email": "wrong-password@example.com",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "wrong-password@example.com",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        update_response = client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Blocked User",
                "email": "blocked@example.com",
                "current_password": "wrongpass123",
            },
        )
        assert update_response.status_code == 400
        assert update_response.json()["detail"] == "Current password is incorrect"


def test_update_profile_rejects_duplicate_email() -> None:
    with TestClient(app) as client:
        first_response = client.post(
            "/auth/register",
            json={
                "name": "First Profile User",
                "email": "first-profile@example.com",
                "password": "password123",
            },
        )
        assert first_response.status_code == 201

        second_response = client.post(
            "/auth/register",
            json={
                "name": "Second Profile User",
                "email": "second-profile@example.com",
                "password": "password123",
            },
        )
        assert second_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "second-profile@example.com",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        update_response = client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Second Profile User",
                "email": "first-profile@example.com",
                "current_password": "password123",
            },
        )
        assert update_response.status_code == 409
        assert update_response.json()["detail"] == "Email already registered"


def test_change_password_invalidates_existing_token() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Password Change User",
                "email": "password-change@example.com",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "password-change@example.com",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        old_token = login_response.json()["access_token"]

        change_response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {old_token}"},
            json={
                "current_password": "password123",
                "new_password": "newpassword123",
            },
        )
        assert change_response.status_code == 200

        old_token_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_token}"},
        )
        assert old_token_response.status_code == 401

        old_password_login_response = client.post(
            "/auth/login",
            json={
                "email": "password-change@example.com",
                "password": "password123",
            },
        )
        assert old_password_login_response.status_code == 401

        new_password_login_response = client.post(
            "/auth/login",
            json={
                "email": "password-change@example.com",
                "password": "newpassword123",
            },
        )
        assert new_password_login_response.status_code == 200


def test_change_password_rejects_wrong_current_password() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Rejected Password Change User",
                "email": "rejected-password-change@example.com",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "rejected-password-change@example.com",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        change_response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrongpass123",
                "new_password": "newpassword123",
            },
        )
        assert change_response.status_code == 400
        assert change_response.json()["detail"] == "Current password is incorrect"
