import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import Settings


def test_development_defaults_accepted():
    os.environ["APP_ENV"] = "development"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = ""
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:3001"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    settings = Settings()
    settings.validate_production()


def test_local_defaults_accepted():
    os.environ["APP_ENV"] = "local"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = ""
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:3001"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    settings = Settings()
    settings.validate_production()


def test_production_requires_jwt_secret():
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://prod:secret@db.example.com:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = ""
    os.environ["CORS_ORIGINS"] = "https://app.example.com"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    settings = Settings()
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY is not configured"):
        settings.validate_production()


def test_production_rejects_default_database_url():
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = "secure-secret-key"
    os.environ["CORS_ORIGINS"] = "https://app.example.com"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    settings = Settings()
    with pytest.raises(RuntimeError, match="DATABASE_URL contains default credentials"):
        settings.validate_production()


def test_production_rejects_postgres_postgres():
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = "secure-secret-key"
    os.environ["CORS_ORIGINS"] = "https://app.example.com"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    settings = Settings()
    with pytest.raises(RuntimeError, match="DATABASE_URL contains default credentials"):
        settings.validate_production()


def test_production_requires_explicit_cors_origins():
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://prod:secret@db.example.com:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = "secure-secret-key"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:3001"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    settings = Settings()
    with pytest.raises(RuntimeError, match="CORS_ORIGINS must be explicitly set in production"):
        settings.validate_production()


def test_production_requires_positive_token_expiry():
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://prod:secret@db.example.com:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = "secure-secret-key"
    os.environ["CORS_ORIGINS"] = "https://app.example.com"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "0"

    settings = Settings()
    with pytest.raises(RuntimeError, match="JWT_ACCESS_TOKEN_EXPIRE_MINUTES must be positive"):
        settings.validate_production()


def test_production_valid_configuration_accepted():
    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://prod:secret@db.example.com:5432/le_seizieme"
    os.environ["JWT_SECRET_KEY"] = "secure-secret-key"
    os.environ["CORS_ORIGINS"] = "https://app.example.com"
    os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

    settings = Settings()
    settings.validate_production()
