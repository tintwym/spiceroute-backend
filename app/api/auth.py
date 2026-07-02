"""Auth-adjacent endpoints.

We do *not* host login/register/password-reset — Firebase Auth does. Once the
client has a Firebase ID token it just calls `GET /auth/me`, which verifies
the token, lazily provisions a local `users` row keyed by `firebase_uid`, and
returns the profile.
"""
from fastapi import APIRouter, Response, status

from app.core.deps import CurrentUser
from app.schemas.user import UserPublic

router = APIRouter()


@router.get("/me", response_model=UserPublic)
async def get_me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)


# ---------------------------------------------------------------------------
# Silent stubs for browser password-manager / extension probes.
#
# Chrome's password manager (and extensions like 1Password, Bitwarden, etc.)
# heuristically POST to guessed URLs such as `/auth/register` and
# `/auth/login` after detecting forms with `autocomplete="new-password"` or
# `current-password`. Our real auth lives in Firebase, so these endpoints have
# no business logic — they just return 204 to keep the dev console clean.
# Hidden from OpenAPI so the public API surface stays accurate.
# ---------------------------------------------------------------------------


@router.api_route(
    "/register",
    methods=["GET", "POST"],
    include_in_schema=False,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def _silence_register_probe() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.api_route(
    "/login",
    methods=["GET", "POST"],
    include_in_schema=False,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def _silence_login_probe() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
