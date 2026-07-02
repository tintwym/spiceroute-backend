import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import ai, auth, health, spice_routes, tags
from app.core.config import get_settings
from app.db.session import engine

log = logging.getLogger(__name__)
settings = get_settings()

# Three-state auth posture, picked at boot:
#
#   1. REAL MODE
#      Credentials are configured (`FIREBASE_CREDENTIALS_JSON` or a
#      file at `FIREBASE_CREDENTIALS_PATH`). Real Firebase ID tokens
#      are verified. This is the production-ready state.
#
#   2. DEV MODE
#      No credentials AND `DEBUG=true`. The verifier accepts
#      `dev:<uid>` synthetic tokens so the test suite and a local dev
#      who hasn't set up a Firebase project yet can still exercise
#      auth-gated endpoints. NEVER ship this state to production —
#      anyone could send `Authorization: Bearer dev:<your_uid>` and
#      impersonate any of your users.
#
#   3. LOCKDOWN MODE  ← the safety net we want for "no creds + !debug"
#      No credentials AND `DEBUG=false`. We boot the service so
#      public endpoints (browse, AI Companion, AI Creator) keep
#      working, but `verify_id_token` REJECTS every token (real and
#      dev) with a clear 503 telling the caller credentials need
#      configuring. This is materially safer than what existed
#      before this safety net (which silently turned every account
#      into a free one for attackers) AND it doesn't hard-fail the
#      boot the way a `raise RuntimeError` here would — operators on
#      PaaS platforms can ship the infrastructure first and add the
#      Firebase secret afterward without the service stopping in
#      between.
#
# The state is determined entirely by Settings + env; nothing else
# in the app needs to branch on it (the firebase service module
# enforces the lockdown in `verify_id_token`).
if settings.firebase_dev_mode and not settings.debug:
    log.error(
        "Firebase is in LOCKDOWN MODE — no credentials configured and "
        "DEBUG=false. Public endpoints work, but every authenticated "
        "request will return 503 until you set FIREBASE_CREDENTIALS_JSON "
        "(or FIREBASE_CREDENTIALS_PATH). This is the safety fallback "
        "for production-shaped deploys that haven't received credentials "
        "yet — it intentionally does NOT accept 'dev:<uid>' tokens, so "
        "no one can impersonate users while you finish the setup."
    )
elif settings.firebase_dev_mode:
    log.warning(
        "Firebase is in DEV MODE — accepting 'dev:<uid>' tokens. "
        "This is gated by DEBUG=true; never set DEBUG=true in production."
    )

# Boot-time guardrail. The DEV-MODE auth + remote-DB combination is
# how production data gets polluted with developer test rows (see the
# postmortem of the `Dev test recipe` row in Neon — local backend
# pointed at the production DATABASE_URL, smoke-tested with a
# `dev:alice` Bearer token, the row was written to prod). The check
# is intentionally narrow: it only fires for that specific three-way
# combination, so REAL MODE and LOCKDOWN MODE boots are unaffected
# regardless of which DB they connect to. See
# `Settings.assert_safe_dev_mode` for the rationale.
settings.assert_safe_dev_mode()


# Lifespan hook: gives long-lived resources (DB pool, the default
# ThreadPoolExecutor used by httpx for blocking name resolution) a
# chance to wind down cleanly on SIGTERM / `uvicorn --reload`. Without
# this, Postgres sees the backend's pooled connections as orphan
# in-progress until they hit the server's idle-in-transaction timeout.
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


# Global 500 handler so unhandled exceptions still come back with CORS
# headers attached. Without this, Starlette's built-in
# `ServerErrorMiddleware` returns a bare 500 BEFORE CORSMiddleware gets
# to add `Access-Control-Allow-Origin`, and browsers misreport the real
# crash as "blocked by CORS policy" — masking the actual cause (DB
# unreachable, missing env var, etc.) behind a misleading network-tab
# error. We catch every exception, log it server-side, and return a
# generic 500 JSON body. CORSMiddleware sits above this in the stack
# so the headers are applied on the way out.
#
# The detail string is deliberately generic — `repr(exc)` would leak
# file paths, package versions, and sometimes credentials into client
# logs. Operators read the real traceback in Render logs instead.
@app.exception_handler(Exception)
async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    log.exception(
        "Unhandled %s on %s %s: %s",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "internal server error"},
    )
