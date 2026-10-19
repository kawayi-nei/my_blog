from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "My Blog API"
    database_url: str
    jwt_secret: str
    jwt_expire_days: int = 7
    admin_username: str = "admin"
    admin_password: str
    admin_enabled: bool = True
    upload_dir: str = str(BASE_DIR / "uploads")
    ip_hash_salt: str
    cookie_secure: bool = False
    site_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
