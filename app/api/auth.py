"""Auth-adjacent endpoints.

We do *not* host login/register/password-reset — Firebase Auth does. Once the
client has a Firebase ID token it just calls `GET /auth/me`, which verifies
the token, lazily provisions a local `users` row keyed by `firebase_uid`, and
returns the profile.
"""
from fastapi import APIRouter

from app.core.deps import CurrentUser
from app.schemas.user import UserPublic

router = APIRouter()


@router.get("/me", response_model=UserPublic)
async def get_me(user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(user)
