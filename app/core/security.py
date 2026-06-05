from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def _encode(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: UUID) -> str:
    return _encode(
        str(user_id),
        timedelta(minutes=settings.access_token_minutes),
        "access",
    )


def create_refresh_token(user_id: UUID) -> str:
    return _encode(
        str(user_id),
        timedelta(days=settings.refresh_token_days),
        "refresh",
    )


def decode_token(token: str, expected_type: str) -> UUID:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise ValueError("invalid token") from exc

    if payload.get("type") != expected_type:
        raise ValueError("wrong token type")

    sub = payload.get("sub")
    if not sub:
        raise ValueError("missing subject")

    try:
        return UUID(sub)
    except ValueError as exc:
        raise ValueError("invalid subject") from exc
