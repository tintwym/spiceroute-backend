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

    # LLM client — OpenAI-compatible Chat Completions HTTP wire format.
    # The same three knobs cover every provider that speaks this protocol:
    # Groq, OpenAI, OpenRouter, Cerebras, Together, and a local Ollama
    # via its `/v1/chat/completions` shim.
    #
    #   `LLM_BASE_URL`  Provider's API root. The client appends
    #                   `/chat/completions` directly. Examples:
    #                     Groq    https://api.groq.com/openai/v1
    #                     OpenAI  https://api.openai.com/v1
    #                     Ollama  http://localhost:11434/v1
    #                   Leave blank to keep the AI endpoints in stub mode.
    #
    #   `LLM_API_KEY`   Bearer token. Required even for local Ollama
    #                   (Ollama ignores the value but the OpenAI-compat
    #                   layer still demands the header — set it to any
    #                   non-empty string, e.g. "ollama"). For Groq /
    #                   OpenAI this is the real secret from the
    #                   provider's dashboard.
    #
    #   `LLM_MODEL`     Model name as the provider recognises it.
    #                   Defaults to Groq's `llama-3.1-8b-instant` since
    #                   that's our recommended free-tier setup. Swap to
    #                   `llama-3.1-70b-versatile` (still free on Groq)
    #                   for higher-quality recipes, or `gpt-4o-mini` /
    #                   `llama3.1:8b` for OpenAI / local Ollama.
    #
    #   `AI_FORCE_STUB` Hard-override that pins the backend to stub mode
    #                   regardless of LLM_BASE_URL. Useful in CI where we
    #                   don't want test runs to probe a network endpoint
    #                   at all. Stub mode also activates implicitly when
    #                   either LLM_BASE_URL or LLM_API_KEY is empty —
    #                   that's how a half-configured Render deploy
    #                   degrades quietly instead of 401-spamming.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "llama-3.1-8b-instant"
    ai_force_stub: bool = False
    # Per-request hard cap on chat-completions calls. The chat path is a
    # stream, so this bounds the connect / first-byte handshake (not the
    # full stream wall clock). Recipe generation is one-shot and uses
    # the full timeout budget for the model to think.
    llm_request_timeout_s: float = 120.0

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

        Triggered by any of:
          * `AI_FORCE_STUB=1` (preferred for CI / offline dev — skips
            the network probe entirely).
          * `LLM_BASE_URL` empty.
          * `LLM_API_KEY` empty. This makes a half-configured deploy
            ("URL set in the blueprint, key not yet pasted in the
            secrets tab") quietly serve stubs instead of spamming 401s
            from the provider.

        Note that an unreachable URL with both knobs set does NOT flip
        this on at config time — the client probes the provider lazily
        on first use and falls back to stubs for that ONE request, so
        a flaky upstream doesn't poison the whole process."""
        if self.ai_force_stub:
            return True
        if not self.llm_base_url.strip():
            return True
        if not self.llm_api_key.strip():
            return True
        return False

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
