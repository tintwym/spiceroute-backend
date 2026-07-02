"""Thin wrapper around Firebase Admin for ID-token verification.

Two modes:

  * REAL — when `firebase-service-account.json` exists, we initialize the SDK
    once and call `auth.verify_id_token(...)` to validate the token signature,
    audience, expiry, and clock skew.

  * DEV — when no credentials file is present, we accept a token of the form
    `dev:<uid>[:<email>][:<name>]` and return a synthetic decoded claim. This
    lets the auth-gated endpoints be exercised by the test suite (and a local
    dev who hasn't bothered to set up a Firebase project yet).

A real Firebase ID token is also valid in REAL mode; the dev shortcut never
overrides real verification.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.core.config import get_settings

log = logging.getLogger(__name__)
_settings = get_settings()

_initialized = False


def _ensure_initialized() -> None:
    global _initialized
    if _initialized or _settings.firebase_dev_mode:
        return
    import firebase_admin
    from firebase_admin import credentials

    # Inline JSON wins when set (the Fly.io / Render / Railway path —
    # there's no file on disk, just a Fly secret containing the JSON
    # content). Falls back to the path-based variant for local dev.
    inline = _settings.firebase_credentials_json.strip()
    if inline:
        import json

        cred = credentials.Certificate(json.loads(inline))
    else:
        cred = credentials.Certificate(_settings.firebase_credentials_path)
    firebase_admin.initialize_app(cred)
    _initialized = True


@dataclass(frozen=True)
class FirebaseUser:
    uid: str
    email: str | None
    display_name: str | None


class FirebaseTokenError(Exception):
    pass


async def verify_id_token(token: str) -> FirebaseUser:
    """Verify a Firebase ID token and return a `FirebaseUser`.

    Raises `FirebaseTokenError` for any failure (invalid sig, expired,
    or no credentials configured in production).

    Three states gated here (see `app/main.py` for the full picture):

      * REAL MODE      — credentials configured; verify with Firebase
      * DEV MODE       — DEBUG=true + no creds; accept `dev:<uid>`
      * LOCKDOWN MODE  — DEBUG=false + no creds; reject EVERYTHING

    NOTE: `firebase_admin.auth.verify_id_token` is a SYNCHRONOUS function
    that performs blocking network I/O (it fetches and caches Google's
    public keys, validates signature/audience/expiry, and on cache miss
    can take 100-300 ms). Running it inline inside FastAPI's async
    handlers would freeze the entire event loop for the duration —
    every concurrent request would queue up serially behind it,
    capping effective throughput at ~3-10 RPS on the auth path.
    We delegate to `asyncio.to_thread` so the blocking call runs in
    the default thread executor and the event loop stays responsive.
    """
    if not token:
        raise FirebaseTokenError("missing token")

    # LOCKDOWN MODE: no credentials AND not in debug. Reject every
    # token (including `dev:<uid>`) so the service can boot in a
    # production-shaped deploy that hasn't received credentials yet
    # WITHOUT exposing an impersonation surface. The caller catches
    # FirebaseTokenError and surfaces a 503 to the client; public
    # (unauthed) endpoints keep working as normal.
    if _settings.firebase_dev_mode and not _settings.debug:
        raise FirebaseTokenError(
            "Authentication is not configured on the server. The operator "
            "needs to set FIREBASE_CREDENTIALS_JSON (or "
            "FIREBASE_CREDENTIALS_PATH) before authenticated endpoints "
            "can be used. Public browsing, AI Companion, and AI Creator "
            "continue to work in the meantime."
        )

    if _settings.firebase_dev_mode and token.startswith("dev:"):
        return _parse_dev_token(token)

    if _settings.firebase_dev_mode:
        raise FirebaseTokenError(
            "Firebase is in dev mode — only `dev:<uid>` tokens are accepted. "
            "Drop firebase-service-account.json into the backend root to "
            "enable real verification."
        )

    # Wrap BOTH the SDK initialisation AND the token verification in the
    # same try/except. Previously `_ensure_initialized()` and the
    # `from firebase_admin import auth` lines lived outside the try
    # block — meaning any failure during SDK boot (malformed
    # `FIREBASE_CREDENTIALS_JSON`, missing file, ImportError, even a
    # google-auth library bug) propagated as an uncaught exception
    # and FastAPI returned HTTP 500. That in turn poisoned every
    # `OptionalCurrentUser`-gated endpoint for signed-in callers:
    # `/spice_routes` would crash for anyone who passed an
    # `Authorization` header, so the Explore grid went blank as
    # soon as the user logged in (the Flutter client just sees a 500
    # and falls through to its empty-list error path).
    #
    # By catching everything here and re-raising as
    # `FirebaseTokenError`, the upstream `OptionalCurrentUser`
    # dependency cleanly demotes the caller to anonymous (returns
    # `None` for the 401 path), so public endpoints keep working
    # even when the backend's Firebase configuration is broken. The
    # operator still sees the original traceback in the Render log
    # (logged below) — they just no longer take the user-facing
    # listing down with them.
    try:
        _ensure_initialized()
        from firebase_admin import auth

        decoded = await asyncio.to_thread(auth.verify_id_token, token)
    except FirebaseTokenError:
        # Already a known token-shape failure (e.g. raised by
        # `_ensure_initialized` itself in a future refactor) — just
        # re-raise so we don't double-wrap the message.
        raise
    except Exception as exc:
        # Distinguish SDK boot failures from token validation
        # failures in the log so the operator knows which one to
        # investigate. "Cannot verify a token because the SDK isn't
        # configured" and "this specific token is bad" both surface
        # as a 401 to the client but mean very different things to
        # the on-call.
        log.warning(
            "verify_id_token failed: %s: %s",
            type(exc).__name__,
            exc,
        )
        raise FirebaseTokenError(str(exc)) from exc

    uid = decoded.get("uid") or decoded.get("user_id")
    if not uid:
        raise FirebaseTokenError("token missing uid")
    return FirebaseUser(
        uid=uid,
        email=decoded.get("email"),
        display_name=decoded.get("name"),
    )


def _parse_dev_token(token: str) -> FirebaseUser:
    # `maxsplit=3` keeps the display-name field intact even when it itself
    # contains colons (e.g. "dev:bob:bob@x.com:Bob: The Great").
    parts = token.split(":", maxsplit=3)
    if len(parts) < 2 or not parts[1]:
        raise FirebaseTokenError("dev token must look like dev:<uid>")
    uid = parts[1]
    email = parts[2] if len(parts) > 2 and parts[2] else f"{uid}@dev.local"
    name = parts[3] if len(parts) > 3 and parts[3] else uid
    return FirebaseUser(uid=uid, email=email, display_name=name)
