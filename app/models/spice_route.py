from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tag import Tag, spice_route_tags


class SpiceRoute(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "spice_routes"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cook_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    ingredients: Mapped[list["Ingredient"]] = relationship(
        back_populates="spice_route",
        cascade="all, delete-orphan",
        order_by="Ingredient.sort_order",
        lazy="selectin",
    )
    steps: Mapped[list["Step"]] = relationship(
        back_populates="spice_route",
        cascade="all, delete-orphan",
        order_by="Step.sort_order",
        lazy="selectin",
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary=spice_route_tags,
        lazy="selectin",
    )


class Ingredient(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ingredients"

    spice_route_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spice_routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    spice_route: Mapped[SpiceRoute] = relationship(back_populates="ingredients")


class Step(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "steps"

    spice_route_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("spice_routes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    spice_route: Mapped[SpiceRoute] = relationship(back_populates="steps")
