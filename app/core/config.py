from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Savor Global Recipes API"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://spiceroute:spiceroute@db:5432/spiceroute"

    cors_origins: str = "*"

    # Firebase Admin — path to the service account JSON downloaded from
    # Firebase Console -> Project Settings -> Service Accounts. Empty value
    # triggers DEV MODE: tokens with the prefix "dev:<uid>" are accepted as a
    # local user. This lets the auth-gated endpoints be developed without a
    # real Firebase project, and lets the test suite run without a key.
    firebase_credentials_path: str = "firebase-service-account.json"
    firebase_project_id: str = ""

    # Google Gemini — empty key triggers stub mode (deterministic mock responses)
    # so the UI is dev-able without a real key. Get one at:
    # https://aistudio.google.com/apikey
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # AI rate limits, keyed by client IP (no auth in v1).
    ai_rate_limit_per_day: int = 30
    ai_chat_per_hour: int = 50

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def gemini_stub_mode(self) -> bool:
        return not self.gemini_api_key.strip()

    @property
    def firebase_dev_mode(self) -> bool:
        """When no Firebase credentials are configured we accept dev tokens of
        the form `dev:<uid>` so the app can be developed without a real
        Firebase project. NEVER let this flip to True in production."""
        from pathlib import Path

        return not Path(self.firebase_credentials_path).is_file()


@lru_cache
def get_settings() -> Settings:
    return Settings()
