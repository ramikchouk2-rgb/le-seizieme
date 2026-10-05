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

    # Step 24C-D-5: maximum accepted profile photo size, in bytes (2 MiB).
    # BYTEA rows live in PostgreSQL, so this is deliberately small; raising it
    # means revisiting table bloat and backup size.
    MAX_PROFILE_PHOTO_BYTES: int = 2 * 1024 * 1024

    # Step 24C-D-6: maximum accepted professional attestation document size
    # (5 MiB). Documents are larger than avatars, but BYTEA storage means the
    # ceiling should stay modest.
    MAX_ATTESTATION_BYTES: int = 5 * 1024 * 1024

    # Step 24C-D-11: server-side profile photo optimization targets.
    #
    # 512 px is derived from how photos are actually displayed, not guessed:
    #   * Print sheet renders a photo at 22 x 27 mm, which is ~260 x 319 device
    #     pixels at 300 DPI (see .print-photo-img in globals.css).
    #   * The largest on-screen use is ServerPhoto size="xl" = 128 CSS px, i.e.
    #     384 device pixels at 3x DPR.
    # 512 px covers both with headroom while staying small enough to download N
    # of them quickly over a phone connection.
    #
    # This is an OPTIMIZATION target, never an upload limit: the accepted upload
    # size stays MAX_PROFILE_PHOTO_BYTES, and a photo already smaller than this
    # is not enlarged.
    PROFILE_PHOTO_MAX_DIMENSION: int = 512

    # Quality 82 is the standard "visually lossless for photographs" point for
    # JPEG. It is high enough that a professional staff photo printed at 22 mm
    # shows no compression artefacts, and low enough to cut a typical 300 KB
    # phone photo to a small fraction of that.
    PROFILE_PHOTO_JPEG_QUALITY: int = 82

    # Photos are re-encoded to JPEG because it is universally decodable, is the
    # smallest sane choice for photographic content, and dropping the source
    # metadata on write is trivial. "image/jpeg" is already permitted by the
    # server_files mime allowlist check constraint.
    PROFILE_PHOTO_OUTPUT_MIME_TYPE: str = "image/jpeg"

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
