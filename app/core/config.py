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

    # Firebase Admin — two ways to provide the credentials:
    #
    #   1. `FIREBASE_CREDENTIALS_PATH` — path to the service-account JSON
    #      downloaded from Firebase Console -> Project Settings ->
    #      Service Accounts. Best for local dev (drop the file at the
    #      repo root and forget about it).
    #
    #   2. `FIREBASE_CREDENTIALS_JSON` — the JSON content inline as a
    #      single string. Best for Fly.io / Render / Railway / Vercel
    #      where you set the credentials via `fly secrets set …` or the
    #      dashboard's env editor and don't want to ship a file. Takes
    #      precedence over the path when both are set.
    #
    # When NEITHER is configured, the backend runs in DEV MODE and accepts
    # tokens of the form "dev:<uid>" — useful for tests and offline dev.
    firebase_credentials_path: str = "firebase-service-account.json"
    firebase_credentials_json: str = ""
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
        Firebase project. NEVER let this flip to True in production.

        Real-mode is unlocked by EITHER an inline JSON env var (preferred
        on hosted platforms — Fly.io, Render, Railway) OR a service-account
        file on disk (preferred locally). If neither resolves, we're in
        dev mode."""
        from pathlib import Path

        if self.firebase_credentials_json.strip():
            return False
        return not Path(self.firebase_credentials_path).is_file()


@lru_cache
def get_settings() -> Settings:
    return Settings()
