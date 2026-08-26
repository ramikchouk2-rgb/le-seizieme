from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/le_seizieme"
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Le Seizième"
    APP_ENV: str = "development"

    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    DEFAULT_EVENT_LATITUDE: float = 36.8065
    DEFAULT_EVENT_LONGITUDE: float = 10.1815

    PORT: int = 8000

    def validate_production(self) -> None:
        if self.APP_ENV != "production":
            if "user:password" in self.DATABASE_URL:
                logger.warning(
                    "DATABASE_URL is using default development credentials. "
                    "Set DATABASE_URL for non-local environments."
                )
            if not self.JWT_SECRET_KEY:
                logger.warning(
                    "JWT_SECRET_KEY is not configured. "
                    "Set JWT_SECRET_KEY for non-local environments."
                )
            return

        if "user:password" in self.DATABASE_URL or "postgres:postgres" in self.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL contains default credentials. "
                "Set a secure DATABASE_URL environment variable."
            )
        if not self.JWT_SECRET_KEY:
            raise RuntimeError(
                "JWT_SECRET_KEY is not configured. "
                "Set a secure JWT_SECRET_KEY environment variable."
            )
        if not self.CORS_ORIGINS or self.CORS_ORIGINS == "http://localhost:3000,http://localhost:3001":
            raise RuntimeError(
                "CORS_ORIGINS must be explicitly set in production. "
                "Set CORS_ORIGINS to your production frontend origin(s)."
            )
        if self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES <= 0:
            raise RuntimeError(
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be positive."
            )


settings = Settings()
