from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "Sentinel Guard"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-strong-random-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Shodan
    SHODAN_API_KEY: str = ""

    # Scanning limits
    MAX_CONCURRENT_SCANS: int = 5
    SCAN_TIMEOUT_SECONDS: int = 300

    # RSA key paths for report signing
    RSA_PRIVATE_KEY_PATH: str = "keys/private.pem"
    RSA_PUBLIC_KEY_PATH: str = "keys/public.pem"

    # Verification
    DNS_VERIFICATION_PREFIX: str = "sentinel-verification"
    HTTP_VERIFICATION_PATH: str = ".well-known/sentinel"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
