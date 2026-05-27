import json
import os
from pathlib import Path

from fastapi.testclient import TestClient


TEST_DB_PATH = Path("/tmp/umkm_food_quality_detect_test.sqlite3")

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{TEST_DB_PATH}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("MODEL_PATH", "ml/model/exp_001_industry_biscuit_only/model.keras")
os.environ.setdefault("CLASS_INDICES_PATH", "ml/model/exp_001_industry_biscuit_only/class_indices.json")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
# Empty string disables domain whitelist so the test image URL is not blocked.
os.environ["ALLOWED_IMAGE_DOMAINS"] = ""

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()


def _expected_active_experiment() -> str:
    config_path = Path("ml/model/active_model.json")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return str(payload["experiment_id"])


def test_detect_endpoint_returns_detection_payload() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Detector User",
                "email": "detector@example.com",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={
                "email": "detector@example.com",
                "password": "password123",
            },
        )
        token = login_response.json()["access_token"]

        detect_response = client.post(
            "/detect",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "image_url": "https://raw.githubusercontent.com/github/explore/main/topics/python/python.png"
            },
        )

        assert detect_response.status_code == 201, detect_response.text
        payload = detect_response.json()
        assert payload["label_key"] in {"layak_jual", "tidak_layak_jual"}
        assert payload["model_version"] == _expected_active_experiment()
        assert isinstance(payload["threshold_used"], float)
        assert 0.0 < payload["threshold_used"] < 1.0
