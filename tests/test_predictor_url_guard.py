import os
from pathlib import Path
from unittest.mock import patch

import pytest


TEST_DB_PATH = Path("/tmp/umkm_food_quality_predictor_guard_test.sqlite3")

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{TEST_DB_PATH}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("MODEL_PATH", "ml/model/umkm_food_quality_v1/model.keras")
os.environ.setdefault("CLASS_INDICES_PATH", "ml/model/umkm_food_quality_v1/class_indices.json")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ["ALLOWED_IMAGE_DOMAINS"] = ""

from app.core.config import get_settings  # noqa: E402
from app.ml.predictor import _validate_image_url_or_raise  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _patch_dns(addresses: list[str]):
    return patch(
        "app.ml.predictor.socket.getaddrinfo",
        return_value=[(0, 0, 0, "", (address, 0)) for address in addresses],
    )


def test_validator_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError, match="http or https"):
        _validate_image_url_or_raise("ftp://example.com/image.jpg")


def test_validator_rejects_loopback_host() -> None:
    with _patch_dns(["127.0.0.1"]):
        with pytest.raises(ValueError, match="non-public IP"):
            _validate_image_url_or_raise("http://localhost/image.jpg")


def test_validator_rejects_aws_metadata_endpoint() -> None:
    with _patch_dns(["169.254.169.254"]):
        with pytest.raises(ValueError, match="non-public IP"):
            _validate_image_url_or_raise("http://169.254.169.254/latest/meta-data/")


def test_validator_rejects_private_rfc1918_host() -> None:
    with _patch_dns(["10.0.0.5"]):
        with pytest.raises(ValueError, match="non-public IP"):
            _validate_image_url_or_raise("http://internal.local/image.jpg")


def test_validator_accepts_public_host_when_no_whitelist() -> None:
    with _patch_dns(["104.16.132.229"]):
        _validate_image_url_or_raise("https://res.cloudinary.com/demo/image.jpg")


def test_validator_enforces_domain_whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_IMAGE_DOMAINS", "res.cloudinary.com")
    get_settings.cache_clear()

    with _patch_dns(["104.16.132.229"]):
        with pytest.raises(ValueError, match="allowed domain list"):
            _validate_image_url_or_raise("https://attacker.com/image.jpg")


def test_validator_accepts_subdomain_of_whitelisted_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_IMAGE_DOMAINS", "cloudinary.com")
    get_settings.cache_clear()

    with _patch_dns(["104.16.132.229"]):
        _validate_image_url_or_raise("https://res.cloudinary.com/demo/image.jpg")


def test_validator_rejects_missing_hostname() -> None:
    with pytest.raises(ValueError, match="hostname"):
        _validate_image_url_or_raise("http:///image.jpg")
