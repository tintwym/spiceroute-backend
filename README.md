# SpiceRoute API

FastAPI + SQLAlchemy + Alembic + PostgreSQL backend for **SpiceRoute**, a multilingual recipe app with an AI Creator (LLM-generated recipes) and an AI Companion (streaming chat). The AI layer speaks the **OpenAI Chat Completions API**, so it drops in against any compatible provider — **[Groq](https://console.groq.com)** (free tier, our default), OpenAI, OpenRouter, Cerebras, Together, or a local **[Ollama](https://ollama.com)** via its `/v1/chat/completions` shim. The client silently falls back to deterministic stub responses when the provider isn't configured or is unreachable. Authentication is delegated to **Firebase Auth** — the API verifies Firebase ID tokens via `firebase-admin` and lazily provisions a local user row keyed by `firebase_uid`.

Runs in Docker. Default DB is [Neon](https://neon.tech) (managed Postgres); a local Docker Postgres profile is included for offline development.

The matching Flutter client lives at **[spiceroute-flutter](https://github.com/tintwym/spiceroute-flutter)**.

## What's in here

```
.
├── app/                        FastAPI application
│   ├── api/                    Route handlers
│   │   ├── auth.py             /auth/me (+ silent stubs for browser pw-mgr probes)
│   │   ├── spice_routes.py     /spice_routes CRUD + filters
│   │   ├── tags.py             /tags autocomplete
│   │   ├── ai.py               /ai/recipe/generate, /ai/chat/stream
│   │   └── health.py           /health
│   ├── core/                   Config, deps, Firebase-Admin bootstrap
│   ├── db/                     SQLAlchemy declarative base + async session
│   ├── models/                 ORM models (User, SpiceRoute, Ingredient, Step, Tag, Cuisine enum)
│   ├── schemas/                Pydantic schemas
│   ├── services/
│   │   ├── firebase.py         Firebase ID-token verifier (real + dev mode)
│   │   ├── spice_routes.py     Ingredient/step builders, tag upsert
│   │   ├── serialization.py    ORM → schema mapping
│   │   └── ai/                 llm.py, prompts.py, rate_limit.py
│   └── main.py                 FastAPI entrypoint (v0.2.0)
├── alembic/                    Database migrations
├── scripts/seed_curated_recipes.py   Seeds 27 curated premium SpiceRoutes
├── tests/                      Pytest suite (auth, recipes, AI; SQLite + asyncio)
├── Dockerfile
├── docker-compose.yml          api (+ optional local Postgres, pgAdmin)
└── pyproject.toml              Python 3.12+, FastAPI, SQLAlchemy 2, httpx (LLM client), firebase-admin
```

## Features

- **Firebase Auth integration** — verifies the bearer ID token on every request, provisions a local `users` row on first sight (`firebase_uid` unique). No password storage, no JWT issuing, no /register endpoint.
- **SpiceRoutes CRUD** with structured ingredients, structured steps, tags, per-recipe language, cuisine, spice level, and a curated `is_premium` flag.
- **Visibility-aware listing** — anonymous callers see public-only; authed callers see public + their own private; `mine=true` returns only their own.
- **Full-text-ish search** across title, description, and ingredient name (`pg_trgm` GIN on Postgres, LIKE on SQLite for tests).
- **Filters**: cuisine, language, tag, `max_minutes`, `premium_only`, `mine`.
- **AI Creator** (`POST /ai/recipe/generate`) — the configured LLM generates a structured recipe; optional `save=true` (auth required) persists it as a public SpiceRoute attributed to the caller.
- **AI Companion** (`POST /ai/chat/stream`) — Server-Sent Events stream of LLM chat deltas for the chat UI.
- **Per-IP rate limiting** for AI endpoints (`AI_RATE_LIMIT_PER_DAY`, `AI_CHAT_PER_HOUR`) so the unauthenticated AI surface is non-trivial to abuse.

## Prerequisites

- Docker + Docker Compose
- A Firebase project (for production-grade auth) — _optional in dev_, see [Dev modes](#dev-modes).
- An LLM API key for real AI — _optional_, see [Dev modes](#dev-modes). [Groq](https://console.groq.com/keys) is free and works out of the box (no GPU host needed). Without one (or with a local Ollama unconfigured) the AI endpoints serve deterministic stub content.

## Quick start

```bash
cp .env.example .env
# Edit .env:
#   - Set DATABASE_URL (Neon or local — see notes below)
#   - Optionally paste a Groq key into LLM_API_KEY (otherwise stub mode);
#     swap LLM_BASE_URL for OpenAI / local Ollama / etc. as needed.
#   - Optionally point FIREBASE_CREDENTIALS_PATH at a real service-account JSON
#     (otherwise dev-mode tokens `dev:<uid>` are accepted)

docker compose up -d --build
```

`api` starts on port 8000 and runs `alembic upgrade head` on startup. Visit:

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

### Database choices

**Option A — Neon (default)**. Connection-string format is documented at the bottom of this README. `.env.example` includes the asyncpg-style URL.

**Option B — Local Docker Postgres**. In `.env`, swap to the `db:5432` URL, then:

```bash
docker compose --profile local-db up -d --build
```

### Seed curated recipes

```bash
docker compose exec api python -m scripts.seed_curated_recipes
```

Idempotent — re-running won't duplicate the 27 curated `is_premium=True` SpiceRoutes.

### Optional pgAdmin (port 5050, login `admin@spiceroute.local` / `admin`):

```bash
docker compose --profile tools up -d
```

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET    | `/health`                              | —        | Liveness + DB ping |
| GET    | `/auth/me`                             | ✓        | Resolves the Firebase ID token, returns the local user profile (auto-provisioned on first call) |
| GET    | `/spice_routes`                        | optional | List + filter (`q`, `cuisine`, `language`, `tag`, `max_minutes`, `premium_only`, `mine`, `limit`, `offset`) |
| POST   | `/spice_routes`                        | ✓        | Create a recipe |
| GET    | `/spice_routes/{id}`                   | optional | Detail (private recipes are 404 for non-owners) |
| PATCH  | `/spice_routes/{id}`                   | ✓ owner  | Partial update |
| DELETE | `/spice_routes/{id}`                   | ✓ owner  | Delete |
| GET    | `/tags`                                | —        | Tag autocomplete (`?q=` substring, `?limit=` 1..200) |
| POST   | `/ai/recipe/generate`                  | optional¹| LLM-generated recipe. `save=true` requires auth |
| POST   | `/ai/chat/stream`                      | —        | SSE stream of LLM chat deltas (`{type: "delta", text}` … `{type: "done"}`) |

¹ Generation itself is anonymous + IP-rate-limited. `save=true` is auth-only — otherwise spam bots could fill the public catalog.

> The `POST /auth/register` and `POST /auth/login` paths exist but return `204` and are hidden from OpenAPI. They're there purely to silence Chrome's password-manager probes — real account creation happens in Firebase, client-side.

## Dev modes

The two heavy external dependencies (Firebase and the LLM provider) each have a built-in dev fallback so the API runs end-to-end with nothing configured.

| Variable | Empty / missing → | Configured → |
|---|---|---|
| `FIREBASE_CREDENTIALS_PATH` | **Dev mode**: any `Authorization: Bearer dev:<uid>` is accepted as user `<uid>`. Tests use this. | Tokens are verified via `firebase-admin`. |
| `LLM_BASE_URL` + `LLM_API_KEY` | **Stub mode** when either is blank or the host is unreachable: AI endpoints return deterministic mock recipes / chat deltas (logged once per request as a warning). | Real `/chat/completions` calls against `LLM_MODEL` (default `llama-3.1-8b-instant` on Groq). |
| `AI_FORCE_STUB` | Off (the client probes the configured provider). | `1` pins the AI layer to stub mode regardless of the URL / key — used by the test suite to avoid network probes. |

> Never let the Firebase fallback flip in production — it's explicitly gated by file/key presence so a misconfigured deploy will start, _but_ won't accept arbitrary `dev:` tokens unless you actively delete the service-account JSON. LLM stub mode is intentionally tolerant: it's expected to be active during initial setup before a key has been pasted, and on hosting tiers that can't reach the provider.

## Tests

```bash
uv venv && source .venv/bin/activate
uv pip install -e . --group dev
pytest
```

19 tests across:

- `tests/test_auth.py` — token verification, lazy user provisioning, dev-mode tokens
- `tests/test_spice_routes.py` — CRUD, visibility rules, search, filters
- `tests/test_ai.py` — recipe-generation happy path, rate-limit guard, save=true auth gate, chat streaming frame format

The pytest suite runs on **in-memory SQLite** (no Postgres required) — `sqlalchemy.Uuid` maps to native UUID on Postgres and `CHAR(32)` on SQLite, and search uses LIKE instead of `pg_trgm`. The asyncio loop is managed by `pytest-asyncio` in `auto` mode.

## Deployment

### Render

A ready-to-use Render Blueprint ([`render.yaml`](./render.yaml)) lives at the root of this backend repo. It declaratively provisions:

- A Docker-backed Web Service that builds from this directory's `Dockerfile`.
- A managed Render Postgres instance (skip / delete that block if you'd rather use Neon).
- All non-secret env vars from [`.env.example`](./.env.example) baked into the blueprint.
- `sync: false` slots for the secrets (`DATABASE_URL`, `FIREBASE_CREDENTIALS_JSON`, `LLM_API_KEY`) that you fill in via the dashboard after the blueprint applies.

The blueprint also:

- Overrides the Dockerfile's dev `--reload` CMD with a production boot bound to Render's injected `$PORT`.
- Runs `alembic upgrade head` as `preDeployCommand` so migrations apply _before_ new traffic shifts.
- Health-checks `/health` (Render marks the deploy failed if it doesn't go green).

#### One-time setup

1. **Push the repo to GitHub** (Render reads `render.yaml` from your default branch).
2. **Render dashboard** → **New +** → **Blueprint** → pick this repo. Render shows you a diff of what it will create; approve.
3. After provisioning finishes, open the new **`spiceroute-api`** service → **Environment** tab → fill in the secrets:

   | Key | How to obtain |
   |---|---|
   | `DATABASE_URL` | If you accepted the blueprint's Postgres: open the `spiceroute-db` service → copy the **External Connection String** → rewrite to the asyncpg format (see below). If using Neon: paste your Neon URL in asyncpg format. |
   | `FIREBASE_CREDENTIALS_JSON` | `cat firebase-service-account.json` from your local machine — paste the entire JSON content. |
   | `LLM_API_KEY` | Free Groq key from <https://console.groq.com/keys> (no credit card). Paste it in. The blueprint pre-fills `LLM_BASE_URL` and `LLM_MODEL` for Groq's `llama-3.1-8b-instant`. Swap to `llama-3.1-70b-versatile` for higher-quality recipes (still free), or change `LLM_BASE_URL` + `LLM_MODEL` to point at OpenAI / OpenRouter / your own Ollama host instead. Leave `LLM_API_KEY` blank to keep the AI endpoints in stub mode. |

   Render's Postgres "External Connection String" looks like:

   ```
   postgres://USER:PASS@dpg-xxx.singapore-postgres.render.com/spiceroute
   ```

   Rewrite it to:

   ```
   postgresql+asyncpg://USER:PASS@dpg-xxx.singapore-postgres.render.com/spiceroute?ssl=require
   ```

4. Click **Save Changes** — Render triggers a deploy automatically. After it goes green, your URL is `https://spiceroute-api.onrender.com` (or whatever name Render assigned — this project's live URL is `https://spiceroute-backend-ggu5.onrender.com`).
5. **Update CORS** — if you renamed the service or attached a custom domain, edit `CORS_ORIGINS` in the blueprint (or directly in the Environment tab) so it lists your Vercel domain(s).

#### Required env / secrets summary

| Variable | Where it's set | Notes |
|---|---|---|
| `DATABASE_URL` | Dashboard (secret) | asyncpg format — `postgresql+asyncpg://…?ssl=require`. |
| `FIREBASE_CREDENTIALS_JSON` | Dashboard (secret) | Service-account JSON inlined as a string (see [Dev modes](#dev-modes)). |
| `LLM_API_KEY` | Dashboard (secret) | Provider API key. Free Groq key from <https://console.groq.com/keys>. Leave blank for stub mode. |
| `CORS_ORIGINS` | `render.yaml` | Public knowledge; lock to your Vercel domain(s). |
| `APP_NAME` / `DEBUG` / `LLM_BASE_URL` / `LLM_MODEL` / `AI_RATE_LIMIT_PER_DAY` / `AI_CHAT_PER_HOUR` | `render.yaml` | Non-sensitive defaults from `.env.example`. |

#### Verifying

```bash
curl https://spiceroute-backend-ggu5.onrender.com/health
# → {"status":"ok","database":"ok"}
```

If `/health` reports `database: down`, your `DATABASE_URL` is wrong — usually missing the `+asyncpg` prefix or using `sslmode=require` (libpq) instead of `ssl=require` (asyncpg). See [Neon URL format](#neon-url-format).

Render's per-service **Logs** tab streams the live application logs. The **Events** tab shows deploy / migration / health-check timelines.

#### Free vs Starter

- **Free** Web Service: sleeps after 15 min of inactivity → cold start is ~30 s. Fine for demos.
- **Starter** Web Service ($7/mo): always-on, no cold start. Recommended once you're sharing the URL.
- **Free** Postgres expires after **90 days** with no warning. Either upgrade to Starter or use [Neon](https://neon.tech) (free forever, just point `DATABASE_URL` at the Neon string).

#### Updating

- `git push origin main` — Render auto-deploys (rebuilds image, runs migrations, swaps zero-downtime).
- Change an env var in the dashboard → Render triggers a rolling restart.

## Architecture notes

- **Auth model**: Firebase is the source of truth. Local `users` rows store `firebase_uid`, optional `email`, and `display_name` (Apple Sign-In with private relay may withhold the email). No passwords, no refresh tokens — token rotation is the client's problem.
- **AI calls** are wrapped with a single-retry policy (`llm.AIError → retry once → 502`). Schema validation against `SpiceRouteCreate` discards extra keys (small models occasionally add `image_prompt`, wrap output in a `recipe:` envelope, etc.) so model drift doesn't break the API.
- **AI stub fallback**: if the LLM provider is unreachable mid-request the client logs a warning and serves stub content for that one request — it does NOT memoize the failure, so the moment the provider comes back it's used again. Keeps "it works on my box" reports honest.
- **AI chat** uses `StreamingResponse` with `text/event-stream` and `X-Accel-Buffering: no` so reverse proxies don't buffer.
- **Rate limits** are stored per-IP in the database (so they survive restarts and apply across replicas, unlike in-memory).
- **Search** uses `pg_trgm` GIN indexes on `spice_routes.title` and `ingredients.name` on Postgres.
- **Cross-database UUIDs**: `sqlalchemy.Uuid` is portable — tests run in-memory without Postgres.

## Environment variables

See [`.env.example`](./.env.example). Defaults are dev-friendly; for real deployments you must override:

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` (see Neon section) |
| `FIREBASE_CREDENTIALS_PATH` | Path to the Firebase service-account JSON. Absent → dev mode. |
| `FIREBASE_PROJECT_ID` | Optional; falls back to the value in the service-account JSON. |
| `LLM_BASE_URL` | Provider's API root for OpenAI-style `/chat/completions`. Default empty (= stub). Examples: `https://api.groq.com/openai/v1`, `https://api.openai.com/v1`, `http://localhost:11434/v1`. |
| `LLM_API_KEY` | Bearer token. Required for Groq / OpenAI / OpenRouter; for local Ollama any non-empty string works. Empty → stub mode (per-request, not memoized). |
| `LLM_MODEL` | Model name as the provider recognizes it. Default `llama-3.1-8b-instant` (Groq). Use `gpt-4o-mini` (OpenAI), `llama3.1:8b` (local Ollama), `llama-3.1-70b-versatile` (Groq, larger), etc. |
| `AI_FORCE_STUB` | `1` pins the AI layer to stub mode regardless of the URL / key. Used by the test suite. |
| `AI_RATE_LIMIT_PER_DAY` | Default `30` — per-IP cap on `/ai/recipe/generate`. |
| `AI_CHAT_PER_HOUR` | Default `50` — per-IP cap on `/ai/chat/stream`. |
| `CORS_ORIGINS` | Comma-separated origins; `*` for local dev. |
| `APP_NAME` | OpenAPI title. Defaults to `SpiceRoute API`. |
| `DEBUG` | FastAPI debug flag. |

### Neon URL format

Neon's web console gives you a libpq-style URL:

```
postgresql://USER:PASS@HOST/DB?channel_binding=require&sslmode=require
```

Convert it for SQLAlchemy + asyncpg by:

1. Prefix `postgresql+asyncpg://` instead of `postgresql://`.
2. Replace `sslmode=require` with `ssl=require` (asyncpg's parameter name).
3. Drop `channel_binding=require` (libpq-only; asyncpg ignores it).
4. Optionally drop `-pooler` from the hostname if you hit prepared-statement compatibility issues.

## License

[MIT](./LICENSE)
