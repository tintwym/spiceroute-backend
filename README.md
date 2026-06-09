# SpiceRoute API

FastAPI + SQLAlchemy + Alembic + PostgreSQL backend for **SpiceRoute**, a multilingual recipe app with an AI Creator (Gemini-generated recipes) and an AI Companion (Gemini streaming chat). Authentication is delegated to **Firebase Auth** — the API verifies Firebase ID tokens via `firebase-admin` and lazily provisions a local user row keyed by `firebase_uid`.

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
│   │   └── ai/                 gemini.py, prompts.py, rate_limit.py
│   └── main.py                 FastAPI entrypoint (v0.2.0)
├── alembic/                    Database migrations
├── scripts/seed_curated_recipes.py   Seeds 27 curated premium SpiceRoutes
├── tests/                      Pytest suite (auth, recipes, AI; SQLite + asyncio)
├── Dockerfile
├── docker-compose.yml          api (+ optional local Postgres, pgAdmin)
└── pyproject.toml              Python 3.12+, FastAPI, SQLAlchemy 2, google-genai, firebase-admin
```

## Features

- **Firebase Auth integration** — verifies the bearer ID token on every request, provisions a local `users` row on first sight (`firebase_uid` unique). No password storage, no JWT issuing, no /register endpoint.
- **SpiceRoutes CRUD** with structured ingredients, structured steps, tags, per-recipe language, cuisine, spice level, and a curated `is_premium` flag.
- **Visibility-aware listing** — anonymous callers see public-only; authed callers see public + their own private; `mine=true` returns only their own.
- **Full-text-ish search** across title, description, and ingredient name (`pg_trgm` GIN on Postgres, LIKE on SQLite for tests).
- **Filters**: cuisine, language, tag, `max_minutes`, `premium_only`, `mine`.
- **AI Creator** (`POST /ai/recipe/generate`) — Gemini generates a structured recipe; optional `save=true` (auth required) persists it as a public SpiceRoute attributed to the caller.
- **AI Companion** (`POST /ai/chat/stream`) — Server-Sent Events stream of Gemini deltas for the chat UI.
- **Per-IP rate limiting** for AI endpoints (`AI_RATE_LIMIT_PER_DAY`, `AI_CHAT_PER_HOUR`) so the unauthenticated AI surface is non-trivial to abuse.

## Prerequisites

- Docker + Docker Compose
- A Firebase project (for production-grade auth) — _optional in dev_, see [Dev modes](#dev-modes).
- A Google AI Studio API key for Gemini — _optional in dev_, see [Dev modes](#dev-modes).

## Quick start

```bash
cp .env.example .env
# Edit .env:
#   - Set DATABASE_URL (Neon or local — see notes below)
#   - Optionally set GEMINI_API_KEY (otherwise stub mode)
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
| POST   | `/ai/recipe/generate`                  | optional¹| Gemini-generated recipe. `save=true` requires auth |
| POST   | `/ai/chat/stream`                      | —        | SSE stream of Gemini chat deltas (`{type: "delta", text}` … `{type: "done"}`) |

¹ Generation itself is anonymous + IP-rate-limited. `save=true` is auth-only — otherwise spam bots could fill the public catalog.

> The `POST /auth/register` and `POST /auth/login` paths exist but return `204` and are hidden from OpenAPI. They're there purely to silence Chrome's password-manager probes — real account creation happens in Firebase, client-side.

## Dev modes

The two heavy external dependencies (Firebase and Gemini) each have a built-in dev fallback so the API runs end-to-end with nothing configured.

| Variable | Empty / missing → | Configured → |
|---|---|---|
| `FIREBASE_CREDENTIALS_PATH` | **Dev mode**: any `Authorization: Bearer dev:<uid>` is accepted as user `<uid>`. Tests use this. | Tokens are verified via `firebase-admin`. |
| `GEMINI_API_KEY` | **Stub mode**: AI endpoints return deterministic mock recipes / chat deltas. | Real Gemini calls (`GEMINI_MODEL`, default `gemini-2.5-flash`). |

> Never let either of these fall back in production — the dev modes are explicitly gated by file/key presence so a misconfigured deploy will start, _but_ won't accept arbitrary `dev:` tokens unless you actively delete the service-account JSON.

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
- Three `sync: false` slots for the secrets (`DATABASE_URL`, `FIREBASE_CREDENTIALS_JSON`, `GEMINI_API_KEY`) that you fill in via the dashboard after the blueprint applies.

The blueprint also:

- Overrides the Dockerfile's dev `--reload` CMD with a production boot bound to Render's injected `$PORT`.
- Runs `alembic upgrade head` as `preDeployCommand` so migrations apply _before_ new traffic shifts.
- Health-checks `/health` (Render marks the deploy failed if it doesn't go green).

#### One-time setup

1. **Push the repo to GitHub** (Render reads `render.yaml` from your default branch).
2. **Render dashboard** → **New +** → **Blueprint** → pick this repo. Render shows you a diff of what it will create; approve.
3. After provisioning finishes, open the new **`spiceroute-api`** service → **Environment** tab → fill in the three secrets:

   | Key | How to obtain |
   |---|---|
   | `DATABASE_URL` | If you accepted the blueprint's Postgres: open the `spiceroute-db` service → copy the **External Connection String** → rewrite to the asyncpg format (see below). If using Neon: paste your Neon URL in asyncpg format. |
   | `FIREBASE_CREDENTIALS_JSON` | `cat firebase-service-account.json` from your local machine — paste the entire JSON content. |
   | `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> |

   Render's Postgres "External Connection String" looks like:

   ```
   postgres://USER:PASS@dpg-xxx.singapore-postgres.render.com/spiceroute
   ```

   Rewrite it to:

   ```
   postgresql+asyncpg://USER:PASS@dpg-xxx.singapore-postgres.render.com/spiceroute?ssl=require
   ```

4. Click **Save Changes** — Render triggers a deploy automatically. After it goes green, your URL is `https://spiceroute-api.onrender.com` (or whatever name you set).
5. **Update CORS** — if you renamed the service or attached a custom domain, edit `CORS_ORIGINS` in the blueprint (or directly in the Environment tab) so it lists your Vercel domain(s).

#### Required env / secrets summary

| Variable | Where it's set | Notes |
|---|---|---|
| `DATABASE_URL` | Dashboard (secret) | asyncpg format — `postgresql+asyncpg://…?ssl=require`. |
| `FIREBASE_CREDENTIALS_JSON` | Dashboard (secret) | Service-account JSON inlined as a string (see [Dev modes](#dev-modes)). |
| `GEMINI_API_KEY` | Dashboard (secret) | Billed API key. |
| `CORS_ORIGINS` | `render.yaml` | Public knowledge; lock to your Vercel domain(s). |
| `APP_NAME` / `DEBUG` / `GEMINI_MODEL` / `AI_RATE_LIMIT_PER_DAY` / `AI_CHAT_PER_HOUR` | `render.yaml` | Non-sensitive defaults from `.env.example`. |

#### Verifying

```bash
curl https://<your-service>.onrender.com/health
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
- **AI calls** are wrapped with a single-retry policy (`gemini.AIError → retry once → 502`). Schema validation against `SpiceRouteCreate` discards extra keys (Gemini occasionally adds `image_prompt`, etc.) so model drift doesn't break the API.
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
| `GEMINI_API_KEY` | Get one at <https://aistudio.google.com/apikey>. Empty → stub mode. |
| `GEMINI_MODEL` | Default `gemini-2.5-flash`. |
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
