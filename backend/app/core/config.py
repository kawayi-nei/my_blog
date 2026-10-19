from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
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
    jwt_secret: str = Field(min_length=32)
    jwt_expire_days: int = 7
    admin_username: str = Field(default="admin", min_length=1, max_length=50)
    admin_password: str = Field(min_length=12)
    admin_enabled: bool = True
    upload_dir: str = str(BASE_DIR / "uploads")
    ip_hash_salt: str
    cookie_secure: bool = False
    site_origin: str = "http://localhost:3000"

    @field_validator("jwt_secret", "admin_password")
    @classmethod
    def reject_placeholders(cls, value: str) -> str:
        if value.startswith("replace-with"):
            raise ValueError("Replace placeholder secrets in .env")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
