from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.tag import Tag, mecipe_tags


class Mecipe(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "mecipes"

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
        back_populates="mecipe",
        cascade="all, delete-orphan",
        order_by="Ingredient.sort_order",
        lazy="selectin",
    )
    steps: Mapped[list["Step"]] = relationship(
        back_populates="mecipe",
        cascade="all, delete-orphan",
        order_by="Step.sort_order",
        lazy="selectin",
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary=mecipe_tags,
        lazy="selectin",
    )


class Ingredient(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ingredients"

    mecipe_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mecipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    mecipe: Mapped[Mecipe] = relationship(back_populates="ingredients")


class Step(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "steps"

    mecipe_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("mecipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    mecipe: Mapped[Mecipe] = relationship(back_populates="steps")
