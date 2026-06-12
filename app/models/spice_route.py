from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.cuisine import Cuisine
from app.models.tag import Tag, spice_route_tags


class SpiceRoute(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "spice_routes"

    user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prep_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cook_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )

    cuisine: Mapped[Cuisine | None] = mapped_column(
        SAEnum(
            Cuisine,
            name="cuisine_type",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
            native_enum=True,
        ),
        nullable=True,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    spice_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Per-locale title + description overrides for users whose UI locale
    # doesn't match `language`. Shape:
    #
    #   {
    #     "my": {"title": "ကြွက်သားနဲ့ ဆားလက်ပန်း", "description": "..."},
    #     "ko": {"title": "키슈 로렌",                  "description": "..."},
    #     "ja": {"title": "キッシュ・ロレーヌ",          "description": "..."},
    #     ...
    #   }
    #
    # The list / detail endpoints accept a `translate_to=<locale>` query
    # param and substitute the matching entry onto the row before
    # serialising. Missing locale → falls back to the original `title` /
    # `description` columns so the response is never blank. Stored as
    # JSONB so we can extend the shape (e.g. translated tagline,
    # alternate ingredient names) without another migration.
    #
    # Why a JSONB column and not a sidecar table:
    #   - Five-or-fewer translations per row; the join overhead and
    #     extra indexes of a sidecar table aren't worth it.
    #   - The translations are 1:1 with the parent row and are always
    #     loaded together — no use case for querying translations
    #     independently or by locale.
    #
    # `with_variant(JSONB(), 'postgresql')` swaps to native PG JSONB
    # in prod (binary storage, GIN-indexable, faster lookups) while
    # keeping plain JSON for the SQLite-backed test suite — the
    # PostgreSQL-specific JSONB type can't compile against SQLite and
    # would otherwise break every test that touches the recipes table.
    translations: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    # Approximate calories for one serving. Always optional — older imports and
    # AI generations that fail to estimate just leave it null and the UI hides
    # the chip.
    calories_per_serving: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

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
