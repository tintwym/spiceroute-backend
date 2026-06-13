from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "SpiceRoute API"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://spiceroute:spiceroute@db:5432/spiceroute"

    # CORS — two complementary knobs:
    #
    #   `CORS_ORIGINS`  Comma-separated explicit allowlist (or "*" for dev).
    #                   Use this for production with fixed domains.
    #
    #   `CORS_ORIGIN_REGEX`  Python regex matched against the request's
    #                        Origin header. Use this when you need a
    #                        wildcard (e.g. all Vercel preview deploys):
    #                          CORS_ORIGIN_REGEX=^https://.*\.vercel\.app$
    #                        When set, this takes precedence over the
    #                        explicit list (FastAPI's CORSMiddleware will
    #                        match either, but regex is the only way to
    #                        do wildcards).
    cors_origins: str = "*"
    cors_origin_regex: str = ""

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

    # Ollama — local LLM runtime. We talk to it over plain HTTP, so the only
    # knobs are the base URL and the model tag.
    #
    #   `OLLAMA_BASE_URL`  Where Ollama listens. Default targets a local
    #                      `ollama serve` on the dev box. In production set
    #                      this to your hosted Ollama URL (a VPS with GPU,
    #                      a Cloudflare-tunneled home server, etc.). When
    #                      Ollama is unreachable we silently fall back to
    #                      stub mode rather than 500ing — useful for the
    #                      Render free tier, where running an 8B model is
    #                      not practical.
    #
    #   `OLLAMA_MODEL`     Model tag to load. The model must already be
    #                      pulled on the Ollama host (`ollama pull
    #                      llama3.1:8b`). Default is `llama3.1:8b` because
    #                      it has solid JSON adherence at a manageable
    #                      footprint (~5 GB).
    #
    #   `AI_FORCE_STUB`    Hard-override that pins the backend to stub mode
    #                      regardless of what `OLLAMA_BASE_URL` says.
    #                      Useful in CI where we don't want test runs to
    #                      probe a network endpoint at all.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ai_force_stub: bool = False
    # Per-request hard cap on Ollama calls. Local models can take a while
    # on CPU; the chat path is a stream so a long wall-clock here just
    # bounds the connect/first-byte handshake, not the whole stream.
    ollama_request_timeout_s: float = 120.0

    # AI rate limits, keyed by client IP (no auth in v1).
    ai_rate_limit_per_day: int = 30
    ai_chat_per_hour: int = 50

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_stub_mode(self) -> bool:
        """True when the AI layer should serve deterministic mock content.

        Triggered by either an explicit `AI_FORCE_STUB=1` (preferred for
        CI / offline dev) or by an empty `OLLAMA_BASE_URL`. Note that an
        unreachable URL does NOT flip this on at config time — the
        client probes Ollama lazily on first use and falls back to stubs
        for that request only, so a flaky local Ollama doesn't poison
        the whole process."""
        return self.ai_force_stub or not self.ollama_base_url.strip()

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
