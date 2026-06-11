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
os.environ["EMAIL_BACKEND"] = "console"
os.environ["PASSWORD_RESET_TOKEN_TTL_MINUTES"] = "15"
os.environ["RESET_PASSWORD_FRONTEND_URL"] = "foodqcheck://reset-password"
os.environ["EMAIL_VERIFICATION_TOKEN_TTL_MINUTES"] = "30"
os.environ["VERIFY_EMAIL_FRONTEND_URL"] = "foodqcheck://verify-email"
os.environ["REQUIRE_VERIFIED_EMAIL"] = "false"
os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from sqlalchemy import select  # noqa: E402

from app.core.password_reset_token import hash_password_reset_token  # noqa: E402
from app.db.models import Detection, EmailVerification, PasswordReset, User  # noqa: E402
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


def test_forgot_password_returns_generic_message_for_unknown_email() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/forgot-password",
            json={"email": "missing@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "If the email exists, a reset link has been sent"


def test_reset_password_accepts_valid_token_and_rejects_reuse() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Reset Password User",
                "email": "reset-password@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        forgot_response = client.post(
            "/auth/forgot-password",
            json={"email": "reset-password@example.com"},
        )
        assert forgot_response.status_code == 200

        with SessionLocal() as db:
            password_reset = db.scalar(select(PasswordReset).order_by(PasswordReset.id.desc()))
            assert password_reset is not None
            reset_token = password_reset.token_hash

        invalid_response = client.post(
            "/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": "Newpassword123",
            },
        )
        assert invalid_response.status_code == 400

        raw_token = "valid-reset-token-for-tests-1234567890"
        with SessionLocal() as db:
            password_reset = db.scalar(select(PasswordReset).order_by(PasswordReset.id.desc()))
            assert password_reset is not None
            password_reset.token_hash = hash_password_reset_token(raw_token)
            db.commit()

        reset_response = client.post(
            "/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "Newpassword123",
            },
        )
        assert reset_response.status_code == 200
        assert reset_response.json()["message"] == "Password has been reset successfully"

        reused_response = client.post(
            "/auth/reset-password",
            json={
                "token": raw_token,
                "new_password": "Anotherpassword123",
            },
        )
        assert reused_response.status_code == 400
        assert reused_response.json()["detail"] == "Invalid or expired password reset token"

        old_password_login_response = client.post(
            "/auth/login",
            json={
                "email": "reset-password@example.com",
                "password": "Password123",
            },
        )
        assert old_password_login_response.status_code == 401

        new_password_login_response = client.post(
            "/auth/login",
            json={
                "email": "reset-password@example.com",
                "password": "Newpassword123",
            },
        )
        assert new_password_login_response.status_code == 200


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

        forgot_response = client.post(
            "/auth/forgot-password",
            json={"email": "delete-account@example.com"},
        )
        assert forgot_response.status_code == 200

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
            remaining_reset = db.scalar(
                select(PasswordReset).where(PasswordReset.user_id == user_id)
            )
            assert deleted_user is None
            assert remaining_detection is None
            assert remaining_reset is None


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


def test_register_sends_email_verification_and_verify_email_succeeds() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Verify Email User",
                "email": "verify-email@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201
        assert register_response.json()["email_verified_at"] is None

        raw_token = "valid-email-verify-token-for-tests-1234567890"
        with SessionLocal() as db:
            verification = db.scalar(select(EmailVerification).order_by(EmailVerification.id.desc()))
            assert verification is not None
            verification.token_hash = hash_password_reset_token(raw_token)
            db.commit()

        verify_response = client.post(
            "/auth/verify-email",
            json={"token": raw_token},
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["message"] == "Email verified successfully"

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == "verify-email@example.com"))
            assert user is not None
            assert user.email_verified_at is not None


def test_register_succeeds_even_if_verification_email_delivery_fails() -> None:
    with patch("app.services.email_verification_service.get_email_sender") as mocked_sender_factory:
        mocked_sender_factory.return_value.send.side_effect = RuntimeError("SMTP unavailable")

        with TestClient(app) as client:
            register_response = client.post(
                "/auth/register",
                json={
                    "name": "Fallback Verify User",
                    "email": "fallback-verify@example.com",
                    "password": "Password123",
                },
            )
            assert register_response.status_code == 201

            with SessionLocal() as db:
                user = db.scalar(select(User).where(User.email == "fallback-verify@example.com"))
                verification = db.scalar(select(EmailVerification).where(EmailVerification.user_id == user.id))
                assert user is not None
                assert verification is not None


def test_forgot_password_succeeds_even_if_email_delivery_fails() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Fallback Reset User",
                "email": "fallback-reset@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

    with patch("app.services.password_reset_service.get_email_sender") as mocked_sender_factory:
        mocked_sender_factory.return_value.send.side_effect = RuntimeError("SMTP unavailable")

        with TestClient(app) as client:
            forgot_response = client.post(
                "/auth/forgot-password",
                json={"email": "fallback-reset@example.com"},
            )
            assert forgot_response.status_code == 200
            assert forgot_response.json()["message"] == "If the email exists, a reset link has been sent"

            with SessionLocal() as db:
                user = db.scalar(select(User).where(User.email == "fallback-reset@example.com"))
                password_reset = db.scalar(select(PasswordReset).where(PasswordReset.user_id == user.id))
                assert user is not None
                assert password_reset is not None


def test_resend_verification_creates_new_record_for_unverified_user() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Resend Verify User",
                "email": "resend-verify@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "resend-verify@example.com",
                "password": "Password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        resend_response = client.post(
            "/auth/resend-verification",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resend_response.status_code == 200
        assert resend_response.json()["message"] == "Verification email sent successfully"

        with SessionLocal() as db:
            verifications = list(db.scalars(select(EmailVerification).where(EmailVerification.user_id == register_response.json()["id"])))
            assert len(verifications) == 1


def test_resend_verification_succeeds_even_if_email_delivery_fails() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Resend Verify Fallback User",
                "email": "resend-verify-fallback@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "resend-verify-fallback@example.com",
                "password": "Password123",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

    with patch("app.services.email_verification_service.get_email_sender") as mocked_sender_factory:
        mocked_sender_factory.return_value.send.side_effect = RuntimeError("SMTP unavailable")

        with TestClient(app) as client:
            resend_response = client.post(
                "/auth/resend-verification",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resend_response.status_code == 200
            assert resend_response.json()["message"] == "Verification email sent successfully"

            with SessionLocal() as db:
                verifications = list(
                    db.scalars(select(EmailVerification).where(EmailVerification.user_id == register_response.json()["id"]))
                )
                assert len(verifications) == 1


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


def test_login_returns_email_verified_at() -> None:
    with TestClient(app) as client:
        client.post(
            "/auth/register",
            json={
                "name": "Token Verify User",
                "email": "token-verify@example.com",
                "password": "Password123",
            },
        )
        response = client.post(
            "/auth/login",
            json={
                "email": "token-verify@example.com",
                "password": "Password123",
            },
        )
        assert response.status_code == 200
        assert response.json()["email_verified_at"] is None


def test_update_profile_resets_email_verified_at_on_email_change() -> None:
    with TestClient(app) as client:
        client.post(
            "/auth/register",
            json={
                "name": "Profile Reset Verify",
                "email": "reset-verify@example.com",
                "password": "Password123",
            },
        )
        login_response = client.post(
            "/auth/login",
            json={
                "email": "reset-verify@example.com",
                "password": "Password123",
            },
        )
        token = login_response.json()["access_token"]

        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == "reset-verify@example.com"))
            assert user is not None
            user.email_verified_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            db.commit()

        update_response = client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Profile Reset Verify",
                "email": "new-email-verify@example.com",
                "current_password": "Password123",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["email_verified_at"] is None


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


def test_login_blocked_when_verification_required_and_not_verified() -> None:
    import app.core.config as config_mod

    original_value = config_mod.get_settings()

    class FakeSettings:
        def __getattr__(self, name: str):
            if name == "require_verified_email":
                return True
            return getattr(original_value, name)

    with patch("app.services.auth_service.get_settings", return_value=FakeSettings()):
        with TestClient(app) as client:
            client.post(
                "/auth/register",
                json={
                    "name": "Blocked Verify User",
                    "email": "blocked-verify@example.com",
                    "password": "Password123",
                },
            )
            response = client.post(
                "/auth/login",
                json={
                    "email": "blocked-verify@example.com",
                    "password": "Password123",
                },
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid email or password"
