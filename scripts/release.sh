#!/usr/bin/env bash
# Release-time tasks run before traffic flips to a new deploy.
#
# Two callers:
#   * Render — wired in render.yaml as `preDeployCommand`. Render aborts
#     the deploy if this exits non-zero.
#   * docker-compose — wired in docker-compose.yml as the boot command
#     prefix. A failure here stops the dev container, which is what you
#     want (you'll see the migration error instead of a confusing 500).
#
# Two phases:
#   1. `alembic upgrade head` — schema migrations. MUST succeed; if it
#      fails the new app code will fail in surprising ways against the
#      old schema. We let this exit non-zero so the caller aborts.
#   2. `seed_curated_recipes --quick` — populate the 27 premium recipes
#      that Explore expects. `--quick` skips the slow image-resolution
#      step for rows that already exist, so this finishes in seconds
#      after the first deploy. Failures are NON-fatal: a transient
#      LoremFlickr/Flickr outage shouldn't block a deploy that's
#      otherwise healthy.
#
# Dev-only `seed_dev_users.py` is NOT called here on purpose; it's
# gated on DEBUG=true and is the wrong thing to run in production.
# `docker-compose.yml` calls it separately for the local dev case.

set -euo pipefail

echo "==> [release] running migrations"
alembic upgrade head

echo "==> [release] seeding curated recipes"
# `|| true` so a transient image-CDN hiccup doesn't fail the deploy.
# The seed is idempotent and re-runs on the next deploy, and the app
# works fine with the rows that already landed.
python -m scripts.seed_curated_recipes --quick || {
  echo "WARN: curated-recipes seed failed; continuing with deploy." >&2
}

echo "==> [release] fixing broken recipe image URLs"
python -m scripts.fix_recipe_images || {
  echo "WARN: recipe image fix failed; continuing with deploy." >&2
}

python -m scripts.audit_recipe_images || {
  echo "WARN: recipe image audit reported issues; see logs." >&2
}

echo "==> [release] backfilling recipe translations (best-effort)"
# Idempotent: only rows missing per-locale bundles are processed.
# Capped per deploy so a full-catalog backfill cannot block traffic
# for hours — set TRANSLATION_BACKFILL_LIMIT=0 to skip, or raise it
# for a one-off catch-up deploy.
if [ -n "${LLM_API_KEY:-}" ] && [ -n "${LLM_BASE_URL:-}" ]; then
  _backfill_limit="${TRANSLATION_BACKFILL_LIMIT:-30}"
  if [ "${_backfill_limit}" -gt 0 ] 2>/dev/null; then
    python -m scripts.backfill_recipe_translations \
      --limit "${_backfill_limit}" --rpm 1 || {
      echo "WARN: translation backfill partial/failed; will retry next deploy." >&2
    }
  else
    echo "==> [release] translation backfill skipped (TRANSLATION_BACKFILL_LIMIT=${_backfill_limit})"
  fi
else
  echo "==> [release] translation backfill skipped (LLM not configured)"
fi

echo "==> [release] done"
