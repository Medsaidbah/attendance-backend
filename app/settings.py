"""Application settings and configuration (Pydantic v2)."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # Database
    # In Docker, Postgres host is the service name "db".
    # Locally (running without Docker), set DATABASE_URL in .env to use "localhost".
    database_url: str = Field(
        default="postgresql://attendance_user:attendance_pass@db:5432/attendance",
        env="DATABASE_URL",
        description="Postgres DSN",
    )

    # JWT Configuration
    jwt_secret_key: str = Field(
        default="your-super-secret-jwt-key-change-this-in-production",
        env="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Admin User Configuration
    admin_user: str = Field(default="admin", env="ADMIN_USER")
    admin_pass: str = Field(default="admin123", env="ADMIN_PASS")

    # Pydantic v2 settings config (replaces class Config)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",   # ignore unexpected env vars
        env_prefix="",    # no prefix required
    )


# Global settings instance
settings = Settings()


