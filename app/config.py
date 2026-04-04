import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./daycare.db"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_ORIGINS: str = "*"
    ENVIRONMENT: str = "development"
    RATE_LIMIT_MAX_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    LOG_LEVEL: str = "INFO"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
