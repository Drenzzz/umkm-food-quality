import json
import os
import socket
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response


TEST_DB_PATH = Path(f"/tmp/umkm_food_quality_detect_test_{os.getpid()}.sqlite3")

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{TEST_DB_PATH}"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["MODEL_PATH"] = "ml/model/umkm_food_quality_v1/model.keras"
os.environ["CLASS_INDICES_PATH"] = "ml/model/umkm_food_quality_v1/class_indices.json"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"
os.environ["ALLOWED_IMAGE_DOMAINS"] = ""

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

from app.core.config import get_settings  # noqa: E402

# Clear cached settings so env vars set above (ALLOWED_HOSTS etc.) take effect
# when the app module is imported below. Without this, a previously cached
# Settings instance from another test module would be reused.
get_settings.cache_clear()

from app.main import app  # noqa: E402

FIXTURE_IMAGE = Path("tests/fixtures/sample_keripik.jpg").read_bytes()
MOCK_IMAGE_URL = "https://mock.example.com/sample.jpg"

# Fake DNS resolution that returns a public IP so the SSRF guard passes.
# The actual HTTP request is intercepted by respx before it hits the network.
_MOCK_DNS = [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]


def _expected_active_experiment() -> str:
    config_path = Path("ml/model/active_model.json")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    return str(payload["experiment_id"])


@pytest.fixture(autouse=True)
def mock_predictor():
    """Mock the ML predictor so tests don't need a real TFLite model."""
    from unittest.mock import AsyncMock, MagicMock

    fake_predictor = MagicMock()
    fake_predictor.predict_from_url = AsyncMock(return_value={
        "label": "Layak Jual",
        "label_key": "layak_jual",
        "confidence_score": 88.5,
        "raw_score": 0.115,
        "threshold_used": 0.3,
        "model_version": "umkm_food_quality_v1",
        "explanation": "Produk menunjukkan ciri visual yang sangat baik.",
    })

    with patch("app.routers.detect.get_predictor", return_value=fake_predictor):
        yield fake_predictor


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


def test_detect_endpoint_returns_detection_payload(mock_image_download) -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "name": "Detector User",
                "email": "detector@example.com",
                "password": "Password123",
            },
        )
        assert register_response.status_code == 201

        login_response = client.post(
            "/auth/login",
            json={"email": "detector@example.com", "password": "Password123"},
        )
        token = login_response.json()["access_token"]

        detect_response = client.post(
            "/detect",
            headers={"Authorization": f"Bearer {token}"},
            json={"image_url": MOCK_IMAGE_URL},
        )

        assert detect_response.status_code == 201, detect_response.text
        payload = detect_response.json()
        assert payload["label_key"] in {"layak_jual", "tidak_layak_jual"}
        assert payload["model_version"] == _expected_active_experiment()
        assert isinstance(payload["threshold_used"], float)
        assert 0.0 < payload["threshold_used"] < 1.0
        assert 0.0 <= payload["confidence_score"] <= 100.0
