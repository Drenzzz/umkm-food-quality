from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CORS_ORIGINS = [
    "http://localhost",
    "capacitor://localhost",
    "ionic://localhost",
]


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    model_path: str = Field(alias="MODEL_PATH")
    class_indices_path: str = Field(alias="CLASS_INDICES_PATH")
    model_registry_path: str = Field(default="ml/model", alias="MODEL_REGISTRY_PATH")
    active_model_config_path: str = Field(default="ml/model/active_model.json", alias="ACTIVE_MODEL_CONFIG_PATH")
    cors_origins: str = Field(alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        configured = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        merged = DEFAULT_CORS_ORIGINS + configured
        return list(dict.fromkeys(merged))


@lru_cache
def get_settings() -> Settings:
    return Settings()
