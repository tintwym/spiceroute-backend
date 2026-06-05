# SpiceRoute API

FastAPI + SQLAlchemy + Alembic + PostgreSQL backend for the **SpiceRoute** recipe management app. Designed to run in Docker, with PostgreSQL hosted on [Neon](https://neon.tech) by default (local Docker Postgres available as a profile).

The matching Flutter client lives at **[spiceroute-mobile](https://github.com/TintWaiYanMin/spiceroute-mobile)**.

## What's in here

```
.
├── app/                    FastAPI application
│   ├── api/                Route handlers (auth, spice_routes, favorites, uploads, tags, health)
│   ├── core/               Config, security, dependencies
│   ├── db/                 SQLAlchemy base + session
│   ├── models/             ORM models (User, SpiceRoute, Ingredient, Step, Tag, Favorite)
│   ├── schemas/            Pydantic schemas
│   ├── services/           Business logic + serialization
│   ├── storage/            Storage backend Protocol + LocalDiskStorage
│   └── main.py             FastAPI entrypoint
├── alembic/                Database migrations
├── scripts/seed.py         Seed demo user + 12 sample SpiceRoutes
├── tests/                  Pytest suite (31 tests)
├── Dockerfile
├── docker-compose.yml      API service (+ optional local Postgres, pgAdmin)
└── pyproject.toml
```

## Features

- Email/password auth with JWT access + refresh tokens (auto-refresh in client)
- CRUD for SpiceRoutes with structured ingredients, structured steps, and tags
- Public/private SpiceRoute flag with visibility-aware queries
- Photo upload (one hero image per SpiceRoute), MIME-validated, served via FastAPI
- Search across title, description, and ingredient names (`pg_trgm` GIN indexes)
- Filter by tag, max total time, mine-only, favorites-only
- Favorites with toggle endpoint + dedicated listing

## Prerequisites

- Docker + Docker Compose

## Quick start

```bash
cp .env.example .env
# Edit .env: set DATABASE_URL (Neon or local), pick a strong JWT_SECRET

docker compose up -d --build
```

`api` starts on port 8000 and runs `alembic upgrade head` on startup. Visit:

- API: <http://localhost:8000>
- Interactive docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

### Database choices

**Option A — Neon (default)**. `.env.example` shows the format. Neon URLs need conversion from libpq to asyncpg syntax (see [.env.example](./.env.example) notes).

**Option B — Local Docker Postgres**. In `.env`, swap to the `db:5432` URL, then:

```bash
docker compose --profile local-db up -d --build
```

### Seed demo data

```bash
docker compose exec api python -m scripts.seed
```

Creates `demo@example.com` / `demopass1` with 12 sample SpiceRoutes. Safe to re-run (skips duplicates).

### Optional pgAdmin (port 5050, login `admin@spiceroute.local` / `admin`):

```bash
docker compose --profile tools up -d
```

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST   | `/auth/register`                       | — | Create account, returns token pair |
| POST   | `/auth/login`                          | — | Returns token pair |
| POST   | `/auth/refresh`                        | — | Exchange refresh for new access |
| GET    | `/auth/me`                             | ✓ | Current user |
| GET    | `/spice_routes`                        | optional | List + filter (`q`, `tag`, `max_minutes`, `mine_only`, `favorites_only`) |
| POST   | `/spice_routes`                        | ✓ | Create |
| GET    | `/spice_routes/{id}`                   | optional | Detail |
| PATCH  | `/spice_routes/{id}`                   | ✓ owner | Update |
| DELETE | `/spice_routes/{id}`                   | ✓ owner | Delete |
| POST   | `/spice_routes/{id}/image`             | ✓ owner | Upload hero image |
| POST   | `/spice_routes/{id}/favorite`          | ✓ | Toggle |
| DELETE | `/spice_routes/{id}/favorite`          | ✓ | Unfavorite |
| GET    | `/me/favorites`                        | ✓ | My favorites |
| GET    | `/tags`                                | — | Autocomplete |
| GET    | `/health`                              | — | Liveness probe |

## Tests

```bash
uv venv && source .venv/bin/activate
uv pip install -e . --group dev
pytest
```

31 tests covering auth, spice_routes CRUD, search, filters, favorites, uploads, visibility rules.

## Architecture notes

- **Auth is JWT** (access ~60 min, refresh ~30 days).
- **Image storage** is `LocalDiskStorage` backed by a Docker volume at `/var/spiceroute-images`. The interface (`app/storage/base.py`) is a `Protocol` — swapping to S3/R2/MinIO/Vercel Blob is one new class, no other code changes.
- **Search** uses `pg_trgm` GIN indexes on `spice_routes.title` and `ingredients.name`. SQLite test fallback uses LIKE — same query, different index path.
- **Cross-database UUIDs**: `sqlalchemy.Uuid` maps to native UUID on Postgres and CHAR(32) on SQLite, so tests run in-memory without Postgres.

## Environment variables

See [.env.example](./.env.example). For real deployments, override `JWT_SECRET`, `DATABASE_URL`, `IMAGE_STORAGE_DIR`, `PUBLIC_IMAGE_BASE_URL`, and `CORS_ORIGINS`.

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
