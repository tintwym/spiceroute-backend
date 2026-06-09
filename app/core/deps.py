import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.services.firebase import FirebaseTokenError, verify_id_token

log = logging.getLogger(__name__)
_settings = get_settings()

# We use HTTPBearer with auto_error=False so we can produce our own 401 body
# (and so OptionalCurrentUser can resolve to None when the header is absent).
_bearer = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str:
    """Best-effort client IP extraction.

    Honors `X-Forwarded-For` so the app behaves correctly behind a typical
    proxy/CDN (Cloudflare, Fly, Railway, Render). When the header has multiple
    hops we take the leftmost (the original client). Falls back to the direct
    socket peer.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        first = fwd.split(",", 1)[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "0.0.0.0"


async def _resolve_user_from_token(
    token: str, db: AsyncSession
) -> User:
    """Verify the Firebase ID token and upsert the local user row.

    The local row is keyed by `firebase_uid`; on first sight we create it,
    on subsequent sights we refresh the email/display_name in case the user
    updated their profile in Firebase.
    """
    try:
        fb_user = await verify_id_token(token)
    except FirebaseTokenError as exc:
        # Distinguish "your token is bad" (client error) from
        # "the server hasn't been configured with Firebase
        # credentials yet" (server-side config error). The latter
        # is what happens when the backend boots in LOCKDOWN MODE
        # (no creds + !debug) — the client should retry once an
        # operator finishes the setup, not prompt the user to sign
        # in again.
        if _settings.firebase_dev_mode and not _settings.debug:
            # Log the operator-facing detail server-side so deploy
            # logs explain the misconfig without leaking the missing
            # env-var name to anonymous callers.
            log.warning(
                "Auth rejected because backend is in LOCKDOWN MODE "
                "(set FIREBASE_CREDENTIALS_JSON to enable auth)."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="authentication service is temporarily unavailable",
            ) from exc
        # Generic 401 — don't echo the underlying exception text to
        # the client. The detail can leak Firebase SDK internals
        # (project IDs, token shapes, line numbers) into client logs.
        log.info("auth rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    result = await db.execute(
        select(User).where(User.firebase_uid == fb_user.uid)
    )
    user = result.scalar_one_or_none()

    dirty = False
    if user is None:
        user = User(
            firebase_uid=fb_user.uid,
            email=fb_user.email,
            display_name=fb_user.display_name or (fb_user.email or fb_user.uid),
        )
        db.add(user)
        dirty = True
    else:
        if fb_user.email and user.email != fb_user.email:
            user.email = fb_user.email
            dirty = True
        if fb_user.display_name and user.display_name != fb_user.display_name:
            user.display_name = fb_user.display_name
            dirty = True

    # Commit identity changes immediately. We don't want a downstream handler's
    # rollback (e.g. payload validation failure on POST) to drop the user row
    # we just provisioned — the next request would then create a duplicate
    # firebase_uid INSERT and 500.
    if dirty:
        try:
            await db.commit()
            await db.refresh(user)
        except IntegrityError:
            # Race: two requests for the same brand-new uid both hit
            # the SELECT-then-INSERT path; one wins, the other sees a
            # UniqueViolation on `users.firebase_uid`. Roll back our
            # failed flush and re-fetch — the winner's row is now
            # visible and represents the same logical user.
            await db.rollback()
            result = await db.execute(
                select(User).where(User.firebase_uid == fb_user.uid)
            )
            user = result.scalar_one()

    return user


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await _resolve_user_from_token(creds.credentials, db)


async def get_current_user_optional(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    if creds is None:
        return None
    try:
        return await _resolve_user_from_token(creds.credentials, db)
    except HTTPException as exc:
        # Optional auth: a *malformed* token is treated as "no user"
        # for routes that work for both anon + authed callers (401).
        # But a server-side config failure (503 lockdown) is NOT a
        # client error — silently demoting an authenticated user to
        # anon would surface as a confusing "404 recipe not found"
        # on their own private recipe, or "401 sign in to save" on
        # the AI creator. Re-raise the 503 so the real cause reaches
        # the client.
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return None
        raise


DbSession = Annotated[AsyncSession, Depends(get_db)]
ClientIP = Annotated[str, Depends(get_client_ip)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[User | None, Depends(get_current_user_optional)]
