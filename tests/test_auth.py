import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


TEST_DB_PATH = Path(f"/tmp/umkm_food_quality_auth_test_{os.getpid()}.sqlite3")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["MODEL_PATH"] = "ml/model/umkm_food_quality_v1/model.keras"
os.environ["CLASS_INDICES_PATH"] = "ml/model/umkm_food_quality_v1/class_indices.json"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from sqlalchemy import select  # noqa: E402

from app.db.models import Detection, User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


def test_auth_register_login_and_me_flow() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201
        assert register_response.json()["email"] == "test@example.com"

        login_response = client.post(
            "/auth/login",
            json={
                "email": "test@example.com",
                "password": "Password123",
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
                "password": "Password123",
            },
        )
        assert first_response.status_code == 201

        second_response = client.post(
            "/auth/register",
            json={
                "name": "Duplicate User Two",
                "email": "duplicate@example.com",
                "password": "Password123",
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
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "profile@example.com",
                "password": "Password123",
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
                "current_password": "Password123",
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
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "wrong-password@example.com",
                "password": "Password123",
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
                "password": "Password123",
            },
        )
        assert first_response.status_code == 201

        second_response = client.post(
            "/auth/register",
            json={
                "name": "Second Profile User",
                "email": "second-profile@example.com",
                "password": "Password123",
            },
        )
        assert second_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "second-profile@example.com",
                "password": "Password123",
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
                "current_password": "Password123",
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
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "password-change@example.com",
                "password": "Password123",
            },
        )
        assert login_response.status_code == 200
        old_token = login_response.json()["access_token"]

        change_response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {old_token}"},
            json={
                "current_password": "Password123",
                "new_password": "Newpassword123",
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
                "password": "Password123",
            },
        )
        assert old_password_login_response.status_code == 401

        new_password_login_response = client.post(
            "/auth/login",
            json={
                "email": "password-change@example.com",
                "password": "Newpassword123",
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
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "rejected-password-change@example.com",
                "password": "Password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        change_response = client.post(
            "/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrongpass123",
                "new_password": "Newpassword123",
            },
        )
        assert change_response.status_code == 400
        assert change_response.json()["detail"] == "Current password is incorrect"


def test_delete_account_removes_user_and_related_records() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Delete Account User",
                "email": "delete-account@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "delete-account@example.com",
                "password": "Password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == "delete-account@example.com"))
            assert user is not None
            user_id = user.id
            db.add(
                Detection(
                    user_id=user_id,
                    image_url="https://example.com/image.jpg",
                    label="Layak Jual",
                    label_key="layak_jual",
                    confidence_score=95.0,
                    raw_score=0.95,
                    threshold_used=0.4,
                    model_version="test-model",
                    explanation="Looks good",
                )
            )
            db.commit()

        delete_response = client.request(
            "DELETE",
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "Password123"},
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Account deleted successfully"

        login_after_delete_response = client.post(
            "/auth/login",
            json={
                "email": "delete-account@example.com",
                "password": "Password123",
            },
        )
        assert login_after_delete_response.status_code == 401

        with SessionLocal() as db:
            deleted_user = db.scalar(select(User).where(User.email == "delete-account@example.com"))
            remaining_detection = db.scalar(
                select(Detection).where(Detection.user_id == user_id)
            )
            assert deleted_user is None
            assert remaining_detection is None


def test_delete_account_rejects_wrong_current_password() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Rejected Delete User",
                "email": "rejected-delete@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "rejected-delete@example.com",
                "password": "Password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        delete_response = client.request(
            "DELETE",
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"current_password": "wrongpass123"},
        )
        assert delete_response.status_code == 400
        assert delete_response.json()["detail"] == "Current password is incorrect"


def test_register_rejects_weak_password_without_uppercase() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "name": "Weak Password User",
                "email": "weak-pw@example.com",
                "password": "lowercase1",
            },
        )
        assert response.status_code == 422


def test_register_rejects_weak_password_without_digit() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "name": "No Digit User",
                "email": "no-digit@example.com",
                "password": "NoDigitPass",
            },
        )
        assert response.status_code == 422


def test_register_rejects_weak_password_without_lowercase() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "name": "No Lower User",
                "email": "no-lower@example.com",
                "password": "NOLOWER1",
            },
        )
        assert response.status_code == 422


def test_register_normalizes_email_to_lowercase() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "name": "Email Norm User",
                "email": "NORM@EXAMPLE.COM",
                "password": "Password123",
            },
        )
        assert response.status_code == 201
        assert response.json()["email"] == "norm@example.com"


def test_register_auto_verifies_email() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "name": "Auto Verify User",
                "email": "auto-verify@example.com",
                "password": "Password123",
            },
        )
        assert response.status_code == 201
        assert response.json()["email_verified_at"] is not None


def test_name_strips_html_tags() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "name": "<b>Bold</b> User",
                "email": "sanitize@example.com",
                "password": "Password123",
            },
        )
        assert response.status_code == 201
        assert response.json()["name"] == "Bold User"
