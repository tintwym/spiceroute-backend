# SpiceRoute API

FastAPI + SQLAlchemy + Alembic + PostgreSQL backend for **SpiceRoute**, a multilingual recipe app with an AI Creator (LLM-generated recipes) and an AI Companion (streaming chat).

The AI layer speaks the **OpenAI Chat Completions API**, so it works with any compatible provider — **[Groq](https://console.groq.com)** (free tier, default), OpenAI, OpenRouter, or local **[Ollama](https://ollama.com)** via `/v1/chat/completions`. When the provider is missing or unreachable, endpoints fall back to deterministic stubs so local dev and CI keep working.

Authentication is **Firebase Auth** — the API verifies ID tokens via `firebase-admin` and lazily provisions a local user row keyed by `firebase_uid`.

Runs in Docker. Default production DB is [Neon](https://neon.tech); a local Docker Postgres profile is included for offline development.

The matching Flutter client: **[spiceroute-flutter](https://github.com/tintwym/spiceroute-flutter)**.

## Features

### Recipes

- **SpiceRoutes CRUD** with structured ingredients, steps, tags, language, cuisine, spice level, calories, difficulty, and `is_premium`.
- **93 curated premium recipes** — seed via `scripts/seed_curated_recipes.py` (idempotent; syncs translations, difficulty, and tags on re-run).
- **31 cuisines** aligned with the Flutter client's region-grouped filter.
- **Visibility-aware listing** — anonymous: public only; signed-in: public + own private; `mine=true` for owned recipes only.
- **Search** across title, description, and ingredient names (`pg_trgm` on Postgres, LIKE on SQLite in tests).
- **Filters** — cuisine, language, tag, `max_minutes`, `premium_only`, `mine`.
- **Pagination** — `limit` (1–100, default 20) and `offset` on list endpoints.
- **Difficulty** — `easy` / `medium` / `hard`; auto-computed on write when omitted.

### Internationalization

- **`translate_to` query param** on list and detail endpoints swaps title, description, ingredients, and steps to the requested locale when translations exist in the row's JSONB `translations` column.
- **Save-time translation** — on create, update, and AI save, `translate_recipe_content` LLM-translates into every supported locale except the source (best-effort; failures never block the save).
- **Backfill script** — `scripts/backfill_recipe_translations.py` fills missing ingredient/step translations for existing rows (idempotent, merges with hand-polished title/description copy).

Supported content languages: `en`, `zh`, `ja`, `ko`, `vi`.

### AI

- **AI Creator** (`POST /ai/recipe/generate`) — structured recipe from an idea; `save=true` (auth required) persists as a public SpiceRoute.
- **AI Companion** (`POST /ai/chat/stream`) — SSE stream of chat deltas.

### Auth & rate limiting

- **Firebase integration** — bearer ID token on protected routes; local `users` row auto-provisioned on first sight. No password storage or `/register` API.
- **Per-IP quotas** (stored in Postgres, survive restarts):
  - Recipe list / detail reads
  - Recipe create / update / delete (`RECIPE_WRITES_PER_DAY`, default 50)
  - AI recipe generation (`AI_RATE_LIMIT_PER_DAY`, default 30)
  - AI chat (`AI_CHAT_PER_HOUR`, default 50)

## Prerequisites

- Docker + Docker Compose
- Firebase project (optional in dev — see [Dev modes](#dev-modes))
- LLM API key (optional — stub mode without one)

## Quick start

```bash
cp .env.example .env
# Set DATABASE_URL, optionally LLM_API_KEY and FIREBASE_CREDENTIALS_PATH

docker compose up -d --build
```

- API: <http://localhost:8000>
- Docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

Migrations run on startup (`alembic upgrade head`).

### Database

**Neon (recommended for production)** — use asyncpg URL format (see [Neon URL format](#neon-url-format)).

**Local Docker Postgres:**

```bash
docker compose --profile local-db up -d --build
```

### Seed curated recipes

```bash
docker compose exec api python -m scripts.seed_curated_recipes
```

Re-running is safe — existing rows are updated, not duplicated.

### Backfill recipe translations

After deploying translation changes, fill missing ingredient/step bundles for existing rows:

```bash
docker compose exec api python -m scripts.backfill_recipe_translations
# Smoke test: --limit 3
# Dry run:    --dry-run
```

Requires a configured LLM (`LLM_API_KEY` + `LLM_BASE_URL`). Free-tier Groq is rate-limited; expect ~30 s per recipe for four locales.

### Optional pgAdmin (port 5050)

```bash
docker compose --profile tools up -d
```

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | — | Liveness + DB ping |
| GET | `/auth/me` | ✓ | Profile (auto-provisioned) |
| GET | `/spice_routes` | optional | List + filter + `translate_to` + `limit` / `offset` |
| POST | `/spice_routes` | ✓ | Create (save-time translation, IP write quota) |
| GET | `/spice_routes/{id}` | optional | Detail + `translate_to` |
| PATCH | `/spice_routes/{id}` | ✓ owner | Partial update (re-translates when content changes) |
| DELETE | `/spice_routes/{id}` | ✓ owner | Delete |
| GET | `/tags` | — | Tag autocomplete |
| POST | `/ai/recipe/generate` | optional¹ | LLM recipe; `save=true` requires auth |
| POST | `/ai/chat/stream` | — | SSE chat stream |

¹ Generation is anonymous + IP-rate-limited; `save=true` is auth-only.

`POST /auth/register` and `POST /auth/login` return `204` to silence browser password-manager probes — real sign-up is client-side Firebase.

## Dev modes

| Variable | Missing → | Set → |
|---|---|---|
| `FIREBASE_CREDENTIALS_PATH` | Dev mode: `Bearer dev:<uid>` accepted | Real Firebase verification |
| `LLM_BASE_URL` + `LLM_API_KEY` | Stub AI responses | Live `/chat/completions` |
| `AI_FORCE_STUB` | Off | `1` forces stub (tests) |

Never run Firebase dev mode in production.

## Tests

```bash
uv venv && source .venv/bin/activate
uv pip install -e . --group dev
pytest
```

**114 tests** — auth, CRUD, visibility, search, `translate_to`, throttling, AI happy paths, LLM client contracts. In-memory SQLite; no Postgres required.

```bash
ruff check .
```

## Deployment

### Render

Blueprint: [`render.yaml`](./render.yaml). After provisioning, set secrets in the dashboard:

| Key | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…?ssl=require` |
| `FIREBASE_CREDENTIALS_JSON` | Full service-account JSON |
| `LLM_API_KEY` | Groq key from [console.groq.com/keys](https://console.groq.com/keys) |

Live URL for this project: `https://spiceroute-backend-ggu5.onrender.com`

```bash
curl https://spiceroute-backend-ggu5.onrender.com/health
# → {"status":"ok","database":"ok"}
```

**Free tier** sleeps after 15 min idle (~30 s cold start). **Starter** ($7/mo) stays warm. Free Render Postgres expires after 90 days — Neon is a durable alternative.

## Architecture notes

- **Auth** — Firebase is source of truth; local rows hold `firebase_uid`, `email`, `display_name`.
- **Translations** — JSONB per row; read path is pure (overrides passed to serializer, ORM never mutated). Malformed JSONB is defensively ignored so Explore never 500s.
- **AI** — single-retry on failure; schema validation strips model drift. Stub fallback is per-request, not memoized.
- **Chat** — `text/event-stream` with `X-Accel-Buffering: no`.
- **Search** — `pg_trgm` GIN indexes on Postgres.
- **UUIDs** — portable across Postgres and SQLite test DB.

## Environment variables

See [`.env.example`](./.env.example).

| Variable | Notes |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` |
| `FIREBASE_CREDENTIALS_PATH` | Service-account JSON path; absent → dev mode |
| `LLM_BASE_URL` | e.g. `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | Bearer token; empty → stub |
| `LLM_MODEL` | Default `llama-3.1-8b-instant` |
| `RECIPE_WRITES_PER_DAY` | Default `50` — per-IP create/update/delete |
| `AI_RATE_LIMIT_PER_DAY` | Default `30` |
| `AI_CHAT_PER_HOUR` | Default `50` |
| `CORS_ORIGINS` | Comma-separated allowed origins |

### Neon URL format

Neon gives libpq-style URLs. Convert for asyncpg:

1. `postgresql+asyncpg://` prefix
2. `sslmode=require` → `ssl=require`
3. Drop `channel_binding=require`

## License

[MIT](./LICENSE)
