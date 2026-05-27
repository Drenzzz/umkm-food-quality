import os
from pathlib import Path

from fastapi.testclient import TestClient


TEST_DB_PATH = Path("/tmp/umkm_food_quality_history_admin_health.sqlite3")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["MODEL_PATH"] = "ml/model/exp_001_industry_biscuit_only/model.keras"
os.environ["CLASS_INDICES_PATH"] = "ml/model/exp_001_industry_biscuit_only/class_indices.json"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
# Empty string disables domain whitelist so the test image URL is not blocked.
os.environ["ALLOWED_IMAGE_DOMAINS"] = ""

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.db.models import Detection, User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

get_settings.cache_clear()


def promote_user_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        user.role = "admin"
        db.commit()


def reset_test_data() -> None:
    with SessionLocal() as db:
        db.query(Detection).delete()
        db.query(User).delete()
        db.commit()


def test_history_admin_and_health_flow() -> None:
    reset_test_data()

    with TestClient(app) as client:
        for email, name in [("user@example.com", "Normal User"), ("admin@example.com", "Admin User")]:
            register_response = client.post(
                "/auth/register",
                json={
                    "name": name,
                    "email": email,
                    "password": "password123",
                },
            )
            assert register_response.status_code == 201

        promote_user_to_admin("admin@example.com")

        user_token = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "password123"},
        ).json()["access_token"]

        admin_token = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "password123"},
        ).json()["access_token"]

        detect_response = client.post(
            "/detect",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"image_url": "https://raw.githubusercontent.com/github/explore/main/topics/python/python.png"},
        )
        assert detect_response.status_code == 201
        detection_id = detect_response.json()["id"]

        history_response = client.get("/history", headers={"Authorization": f"Bearer {user_token}"})
        assert history_response.status_code == 200
        assert len(history_response.json()["items"]) == 1

        detail_response = client.get(f"/history/{detection_id}", headers={"Authorization": f"Bearer {user_token}"})
        assert detail_response.status_code == 200
        assert detail_response.json()["id"] == detection_id

        dashboard_response = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert dashboard_response.status_code == 200
        assert dashboard_response.json()["total_detections"] == 1

        admin_detections_response = client.get("/admin/detections", headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_detections_response.status_code == 200
        assert len(admin_detections_response.json()["items"]) == 1

        forbidden_dashboard = client.get("/admin/dashboard", headers={"Authorization": f"Bearer {user_token}"})
        assert forbidden_dashboard.status_code == 403

        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"
