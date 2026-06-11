import os
import socket
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response


TEST_DB_PATH = Path(f"/tmp/umkm_food_quality_history_admin_health_{os.getpid()}.sqlite3")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["MODEL_PATH"] = "ml/model/umkm_food_quality_v1/model.keras"
os.environ["CLASS_INDICES_PATH"] = "ml/model/umkm_food_quality_v1/class_indices.json"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["EMAIL_BACKEND"] = "console"
os.environ["VERIFY_EMAIL_FRONTEND_URL"] = "http://localhost:5173/verify-email"
os.environ["ALLOWED_IMAGE_DOMAINS"] = ""

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.models import Detection, User  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()

FIXTURE_IMAGE = Path("tests/fixtures/sample_keripik.jpg").read_bytes()
MOCK_IMAGE_URL = "https://mock.example.com/sample.jpg"

_MOCK_DNS = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]


@pytest.fixture()
def mock_image_download():
    with patch("app.ml.predictor.socket.getaddrinfo", return_value=_MOCK_DNS):
        with respx.mock(assert_all_called=False) as mock:
            mock.get(MOCK_IMAGE_URL).mock(
                return_value=Response(
                    200,
                    content=FIXTURE_IMAGE,
                    headers={"content-type": "image/jpeg"},
                )
            )
            yield mock


def promote_user_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == email).one()
        user.role = "admin"
        db.commit()


def reset_test_data() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.query(Detection).delete()
        db.query(User).delete()
        db.commit()


def test_history_admin_and_health_flow(mock_image_download) -> None:
    reset_test_data()

    with TestClient(app) as client:
        for email, name in [("user@example.com", "Normal User"), ("admin@example.com", "Admin User")]:
            register_response = client.post(
                "/auth/register",
                json={"name": name, "email": email, "password": "password123"},
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
            json={"image_url": MOCK_IMAGE_URL},
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


def test_history_delete_single_and_bulk_respects_user_scope() -> None:
    reset_test_data()

    with TestClient(app) as client:
        first_register = client.post(
            "/auth/register",
            json={"name": "History User One", "email": "history-one@example.com", "password": "password123"},
        )
        assert first_register.status_code == 201

        second_register = client.post(
            "/auth/register",
            json={"name": "History User Two", "email": "history-two@example.com", "password": "password123"},
        )
        assert second_register.status_code == 201

        first_token = client.post(
            "/auth/login",
            json={"email": "history-one@example.com", "password": "password123"},
        ).json()["access_token"]

        second_token = client.post(
            "/auth/login",
            json={"email": "history-two@example.com", "password": "password123"},
        ).json()["access_token"]

        with SessionLocal() as db:
            first_user = db.query(User).filter(User.email == "history-one@example.com").one()
            second_user = db.query(User).filter(User.email == "history-two@example.com").one()
            db.add_all(
                [
                    Detection(
                        user_id=first_user.id,
                        image_url="https://example.com/one-a.jpg",
                        label="Layak Jual",
                        label_key="layak_jual",
                        confidence_score=88.0,
                        raw_score=0.88,
                        threshold_used=0.4,
                        model_version="test-model",
                        explanation="First user item A",
                    ),
                    Detection(
                        user_id=first_user.id,
                        image_url="https://example.com/one-b.jpg",
                        label="Tidak Layak Jual",
                        label_key="tidak_layak_jual",
                        confidence_score=64.0,
                        raw_score=0.64,
                        threshold_used=0.4,
                        model_version="test-model",
                        explanation="First user item B",
                    ),
                    Detection(
                        user_id=second_user.id,
                        image_url="https://example.com/two-a.jpg",
                        label="Layak Jual",
                        label_key="layak_jual",
                        confidence_score=91.0,
                        raw_score=0.91,
                        threshold_used=0.4,
                        model_version="test-model",
                        explanation="Second user item A",
                    ),
                ]
            )
            db.commit()

            first_ids = [item.id for item in db.query(Detection).filter(Detection.user_id == first_user.id).order_by(Detection.id.asc())]
            second_ids = [item.id for item in db.query(Detection).filter(Detection.user_id == second_user.id).order_by(Detection.id.asc())]

        forbidden_delete = client.delete(
            f"/history/{second_ids[0]}",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert forbidden_delete.status_code == 404

        single_delete = client.delete(
            f"/history/{first_ids[0]}",
            headers={"Authorization": f"Bearer {first_token}"},
        )
        assert single_delete.status_code == 200
        assert single_delete.json()["deleted_count"] == 1

        bulk_delete = client.request(
            "DELETE",
            "/history",
            headers={"Authorization": f"Bearer {first_token}"},
            json={"ids": [first_ids[1], second_ids[0]]},
        )
        assert bulk_delete.status_code == 200
        assert bulk_delete.json()["deleted_count"] == 1

        first_history = client.get("/history", headers={"Authorization": f"Bearer {first_token}"})
        assert first_history.status_code == 200
        assert first_history.json()["items"] == []

        second_history = client.get("/history", headers={"Authorization": f"Bearer {second_token}"})
        assert second_history.status_code == 200
        assert len(second_history.json()["items"]) == 1
