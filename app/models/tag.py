from sqlalchemy import Column, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

spice_route_tags = Table(
    "spice_route_tags",
    Base.metadata,
    Column("spice_route_id", Uuid(as_uuid=True), ForeignKey("spice_routes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Uuid(as_uuid=True), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
