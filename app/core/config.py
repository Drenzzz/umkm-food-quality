from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CORS_ORIGINS: list[str] = []


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    model_path: str = Field(alias="MODEL_PATH")
    class_indices_path: str = Field(alias="CLASS_INDICES_PATH")
    model_registry_path: str = Field(default="ml/model", alias="MODEL_REGISTRY_PATH")
    active_model_config_path: str = Field(default="ml/model/active_model.json", alias="ACTIVE_MODEL_CONFIG_PATH")
    model_quality_report_path: str = Field(default="ml/model/model_quality_report.json", alias="MODEL_QUALITY_REPORT_PATH")
    model_quality_strict: bool = Field(default=False, alias="MODEL_QUALITY_STRICT")
    enable_multi_model_comparison: bool = Field(default=False, alias="ENABLE_MULTI_MODEL_COMPARISON")
    cors_origins: str = Field(alias="CORS_ORIGINS")
    allowed_image_domains: str = Field(default="", alias="ALLOWED_IMAGE_DOMAINS")
    image_download_max_bytes: int = Field(default=10 * 1024 * 1024, alias="IMAGE_DOWNLOAD_MAX_BYTES")
    image_download_max_redirects: int = Field(default=3, alias="IMAGE_DOWNLOAD_MAX_REDIRECTS")
    image_download_timeout_seconds: float = Field(default=20.0, alias="IMAGE_DOWNLOAD_TIMEOUT_SECONDS")
    warmup_predictor_on_startup: bool = Field(default=True, alias="WARMUP_PREDICTOR_ON_STARTUP")
    allowed_hosts: str = Field(default="localhost,127.0.0.1", alias="ALLOWED_HOSTS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        configured = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        merged = DEFAULT_CORS_ORIGINS + configured
        return list(dict.fromkeys(merged))

    @property
    def allowed_image_domain_list(self) -> list[str]:
        return [domain.strip().lower() for domain in self.allowed_image_domains.split(",") if domain.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
