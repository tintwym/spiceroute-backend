# `scripts/` — release tasks & seeders

Three short scripts that together keep a fresh database from looking
empty. All are idempotent so calling them more than once is safe.

| File | When it runs | What it does | Required env |
|---|---|---|---|
| `release.sh` | Every Render deploy (`preDeployCommand` in `render.yaml`) and every `docker compose up` boot | Runs migrations, curated-recipes quick seed, then a capped translation backfill when `LLM_*` is configured | `DATABASE_URL`, optional `LLM_BASE_URL` + `LLM_API_KEY` |
| `backfill_recipe_translations.py` | After adding cuisines/recipes; also called by `release.sh` (15 rows/deploy by default) | LLM-fills `spice_routes.translations` (title, description, ingredients, steps) for rows missing locale bundles | `DATABASE_URL`, `LLM_BASE_URL`, `LLM_API_KEY` |
| `seed_curated_recipes.py` | Called by `release.sh`; can also be invoked by hand | Inserts the 93 hand-curated `is_premium=True` recipes that drive the Explore tab — 3 per cuisine across all 31 cuisines, with full ingredients, steps, tags, and (lazily verified) Flickr/Wikimedia images | `DATABASE_URL` |
| `seed_dev_users.py` | Local dev only, called by `docker-compose.yml` after `release.sh` (and refuses to run unless `DEBUG=true`) | Inserts 3 sample users (`alice`, `bob`, `carol`) plus 2 authored recipes each, so the dev-auth stub tokens (`Authorization: Bearer dev:alice`) have something to show on My Recipes | `DATABASE_URL`, `DEBUG=true` |

## Running by hand

```bash
# Fresh local DB, no Docker: do everything.
bash scripts/release.sh
DEBUG=true uv run python -m scripts.seed_dev_users

# Re-resolve dead Flickr image URLs on the curated 27.
# Skip --quick to force a full network check; takes ~30s.
uv run python -m scripts.seed_curated_recipes

# Same thing inside Docker.
docker compose exec api bash scripts/release.sh
docker compose exec api python -m scripts.seed_dev_users
```

## Adding more curated recipes

`scripts/curated_data.py` holds the spec (`CURATED`). Append a new
entry following the `RecipeSpec` TypedDict; the seed picks it up
automatically. To wire course/dietary tags on it for the Explore filter
dropdowns, also append to `_EXTRA_TAGS_BY_TITLE` in
`seed_curated_recipes.py`.

Image guidance: prefer a hand-picked `upload.wikimedia.org` URL for new
entries — those are permanent and the seeder uses them as-is. Falling
back to LoremFlickr keywords works but degrades over years as Flickr
photos go private; you'll get the occasional placeholder.

## Adding more dev recipes

Edit `_DEV_RECIPES` in `seed_dev_users.py`. Each entry needs an
`owner_uid` matching one of the three users (`alice`, `bob`, `carol`)
or you can add to `_DEV_USERS` first.

## Production safety

`release.sh` is what runs in production. It migrates, quick-seeds
curated recipes, then backfills up to `TRANSLATION_BACKFILL_LIMIT`
recipe translations per deploy (default **15**, set to **0** to skip).
For a one-off full catch-up after a big expansion:

```bash
uv run python -m scripts.backfill_recipe_translations
```

It never calls `seed_dev_users.py` — that script also self-checks
`DEBUG=true` as a belt-and-braces measure, so an accidental call in
prod would refuse to run rather than create fake users in your live
database.
