from functools import lru_cache
from typing import List

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

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
