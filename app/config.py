import os
from functools import lru_cache
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Runtime configuration for the Android Aid backend."""

    app_env: str = "dev"
    app_name: str = "android-aid-backend"
    app_version: str = "0.1.0"
    claude_api_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    cors_allow_origins: list[str] = ["*"]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_env=os.getenv("APP_ENV", "dev"),
            claude_api_key=os.getenv("CLAUDE_API_KEY") or None,
            groq_api_key=os.getenv("GROQ_API_KEY") or None,
            groq_model=os.getenv(
                "GROQ_MODEL",
                "llama-3.3-70b-versatile",
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()