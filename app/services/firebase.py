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

    Raises `FirebaseTokenError` for any failure (invalid sig, expired, etc.).

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

    if _settings.firebase_dev_mode and token.startswith("dev:"):
        return _parse_dev_token(token)

    if _settings.firebase_dev_mode:
        raise FirebaseTokenError(
            "Firebase is in dev mode — only `dev:<uid>` tokens are accepted. "
            "Drop firebase-service-account.json into the backend root to "
            "enable real verification."
        )

    _ensure_initialized()
    from firebase_admin import auth

    try:
        decoded = await asyncio.to_thread(auth.verify_id_token, token)
    except Exception as exc:
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
