import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import ai, auth, health, spice_routes, tags
from app.core.config import get_settings
from app.db.session import engine

log = logging.getLogger(__name__)
settings = get_settings()

# CRITICAL safety gate: refuse to boot if the backend would accept dev
# tokens in a production-shaped environment.
#
# Dev mode flips ON whenever NEITHER `FIREBASE_CREDENTIALS_JSON` nor a
# file at `FIREBASE_CREDENTIALS_PATH` is present. In any container/PaaS
# deploy (Render, Fly, Railway, Vercel) the file is NOT shipped — it has
# to be supplied via the inline env var. If an operator forgets to paste
# `FIREBASE_CREDENTIALS_JSON` in the Render dashboard, the service would
# come up perfectly happy AND start accepting `Authorization: Bearer
# dev:<victim_uid>` tokens, granting full impersonation of any user.
# Hard-failing the boot makes the misconfig instantly visible (Render's
# health check goes red on first startup) instead of silently turning
# every account into a free one for attackers.
#
# Locally, `DEBUG=true` is the explicit opt-in to dev-mode auth.
if settings.firebase_dev_mode and not settings.debug:
    raise RuntimeError(
        "Refusing to boot: Firebase is in DEV MODE (no credentials "
        "configured) but DEBUG=false suggests production. In this state "
        "the API would accept any 'dev:<uid>' bearer token as that user, "
        "letting anyone impersonate anyone. Set FIREBASE_CREDENTIALS_JSON "
        "(or FIREBASE_CREDENTIALS_PATH) before starting the service. If "
        "this IS a local dev session, set DEBUG=true."
    )

if settings.firebase_dev_mode:
    log.warning(
        "Firebase is in DEV MODE — accepting 'dev:<uid>' tokens. "
        "This is gated by DEBUG=true; never set DEBUG=true in production."
    )


# Lifespan hook: gives long-lived resources (DB pool, in-flight chat
# producer threads via the default ThreadPoolExecutor) a chance to
# wind down cleanly on SIGTERM / `uvicorn --reload`. Without this,
# Postgres sees the backend's pooled connections as orphan in-progress
# until they hit the server's idle-in-transaction timeout, and Gemini
# producer threads keep draining responses we no longer care about.
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    log.info("application starting")
    try:
        yield
    finally:
        log.info("application shutting down — disposing DB engine")
        # Close all pooled connections and release the engine's
        # internal background tasks. Safe to call even if engine
        # was never used (no-op when the pool is empty).
        await engine.dispose()
        log.info("DB engine disposed")


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS — passes BOTH an explicit allowlist and (optionally) a regex so
# operators can mix exact origins with wildcards. The middleware
# considers a request OK if EITHER matches the request's Origin header,
# which is how Vercel preview deploys (`https://*.vercel.app`) can hit
# the same backend that also serves a fixed production domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(spice_routes.router, prefix="/spice_routes", tags=["spice_routes"])
app.include_router(tags.router, prefix="/tags", tags=["tags"])
app.include_router(ai.router, prefix="/ai", tags=["ai"])
