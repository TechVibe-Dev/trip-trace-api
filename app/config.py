from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    # 180 days — sessions are meant to last months, matching typical app UX.
    # Single long-lived JWT (no refresh token): simpler, but can't be
    # revoked server-side before it expires (see decision in README/issue).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 259200
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    GOOGLE_ROUTES_API_KEY: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def pin_postgres_driver(cls, url: str) -> str:
        # SQLAlchemy 2.1 maps a bare postgresql:// URL to psycopg (v3), but
        # only psycopg2 is installed, so pin the driver explicitly.
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg2://" + url[len(prefix):]
        return url

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
