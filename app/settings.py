"""Application settings and configuration (Pydantic v2)."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # Database (Docker uses host "db")
    database_url: str = Field(
        default="postgresql://attendance_user:attendance_pass@db:5432/attendance",
        env="DATABASE_URL",
        description="Postgres DSN",
    )

    # JWT
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-this-in-production",
        env="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Admin user
    admin_user: str = Field(default="admin", env="ADMIN_USER")
    admin_pass: str = Field(default="admin123", env="ADMIN_PASS")

    # ✅ HMAC for mobile ingestion
    api_key_app: Optional[str] = Field(default=None, env="API_KEY_APP")
    signing_secret: Optional[str] = Field(default=None, env="SIGNING_SECRET")

    # Optional attendance tuning
    attendance_grace_minutes: int = Field(default=0, env="ATTENDANCE_GRACE_MINUTES")

    # Pydantic v2 settings
    model_config = SettingsConfigDict(
        env_file=".env",               # also reads OS env from Docker Compose
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="",                 # no prefix
    )

    # ---- Backwards-compat properties (UPPERCASE) ----
    @property
    def API_KEY_APP(self) -> Optional[str]:
        return self.api_key_app

    @property
    def SIGNING_SECRET(self) -> Optional[str]:
        return self.signing_secret


# Global settings instance
settings = Settings()
