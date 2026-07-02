from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    # Firebase UID is the source of truth. Email is informational and may be
    # absent (Apple Sign-In with private relay can withhold it).
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    email: Mapped[str | None] = mapped_column(
        String(255), unique=False, nullable=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
