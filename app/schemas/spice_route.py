from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.cuisine import Cuisine

NameStr = Annotated[str, Field(min_length=1, max_length=200)]

# Must stay in sync with the Flutter app's supported locales
# (spiceroute-flutter/lib/l10n/*.arb). The product swapped Thai out for
# Burmese ("my") earlier — backend was not updated, so every Burmese
# AI generate/chat/save call returned 422 with the misleading error
# "language must be one of (en, zh, my, ja, ko, vi)". Burmese (`my`)
# replaced Thai (`th`) in v2 — the old `th` is intentionally NOT
# accepted any more; rows persisted under `th` from earlier deploys
# were migrated in `alembic/versions/0002_savor_global.py`.
SUPPORTED_LANGUAGES = ("en", "zh", "my", "ja", "ko", "vi")


class IngredientIn(BaseModel):
    quantity: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=32)
    name: NameStr


class IngredientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    quantity: Decimal | None
    unit: str | None
    name: str
    sort_order: int


class StepIn(BaseModel):
    body: str = Field(min_length=1)


class StepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sort_order: int
    body: str


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class SpiceRouteBase(BaseModel):
    title: NameStr
    description: str | None = None
    prep_minutes: int = Field(default=0, ge=0, le=10_000)
    cook_minutes: int = Field(default=0, ge=0, le=10_000)
    servings: int = Field(default=1, ge=1, le=1000)
    cuisine: Cuisine | None = None
    language: str = Field(default="en", min_length=2, max_length=8)
    spice_level: int = Field(default=0, ge=0, le=3)
    is_public: bool = True
    is_premium: bool = False
    calories_per_serving: int | None = Field(default=None, ge=0, le=20_000)

    @field_validator("language")
    @classmethod
    def _normalize_lang(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"language must be one of {SUPPORTED_LANGUAGES}; got {v!r}"
            )
        return v


class SpiceRouteCreate(SpiceRouteBase):
    ingredients: list[IngredientIn] = Field(default_factory=list, max_length=200)
    steps: list[StepIn] = Field(default_factory=list, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=50)
    image_url: str | None = Field(default=None, max_length=500)

    @field_validator("is_premium")
    @classmethod
    def _reject_client_premium(cls, v: bool) -> bool:
        # `is_premium` is server-controlled — only the curated seed
        # script sets it. Before this validator, the field was accepted
        # but silently overridden to False inside the route handler,
        # which masked client mistakes (a client thinking it was
        # successfully publishing a "premium" recipe). Reject loudly
        # so callers see the field isn't theirs to set.
        if v:
            raise ValueError(
                "is_premium is server-managed; clients cannot set it"
            )
        return v

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for t in v:
            n = t.strip().lower()
            if n and n not in seen and len(n) <= 64:
                seen.add(n)
                cleaned.append(n)
        return cleaned


class SpiceRouteUpdate(BaseModel):
    """Partial update — every field is optional. Only fields that are
    explicitly provided will be applied. Use `model_dump(exclude_unset=True)`
    on the server side to distinguish "field absent" from "field set to None"."""

    title: NameStr | None = None
    description: str | None = None
    prep_minutes: int | None = Field(default=None, ge=0, le=10_000)
    cook_minutes: int | None = Field(default=None, ge=0, le=10_000)
    servings: int | None = Field(default=None, ge=1, le=1000)
    cuisine: Cuisine | None = None
    language: str | None = Field(default=None, min_length=2, max_length=8)
    spice_level: int | None = Field(default=None, ge=0, le=3)
    is_public: bool | None = None
    calories_per_serving: int | None = Field(default=None, ge=0, le=20_000)
    image_url: str | None = Field(default=None, max_length=500)
    ingredients: list[IngredientIn] | None = Field(default=None, max_length=200)
    steps: list[StepIn] | None = Field(default=None, max_length=200)
    tags: list[str] | None = Field(default=None, max_length=50)

    @field_validator("language")
    @classmethod
    def _normalize_lang(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"language must be one of {SUPPORTED_LANGUAGES}; got {v!r}"
            )
        return v

    @field_validator(
        "prep_minutes",
        "cook_minutes",
        "servings",
        "language",
        "spice_level",
        "is_public",
        mode="before",
    )
    @classmethod
    def _reject_explicit_none(cls, v: object, info) -> object:
        """Reject `{"field": null}` on columns that map to non-nullable
        SQL columns. Pydantic's `Optional[T]` syntax allowed any
        client to send `{"language": null}` (or null for prep_minutes,
        cook_minutes, servings, spice_level, is_public), which the
        PATCH handler would `setattr` onto the ORM and then crash
        with a 500 on `commit()` when the DB rejected the NOT NULL
        violation. The intent of `Optional` here is "unset = leave
        alone", NOT "set to null"; the distinction matters because
        the underlying columns ARE non-nullable.

        Allowing an explicit null only for fields that ARE nullable
        on the model (cuisine, calories_per_serving, image_url,
        description, ingredients, steps, tags) keeps the explicit
        "clear this field" affordance for those columns.
        """
        if v is None:
            raise ValueError(
                f"{info.field_name} cannot be null; "
                "omit the field to leave it unchanged"
            )
        return v

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        cleaned: list[str] = []
        seen: set[str] = set()
        for t in v:
            n = t.strip().lower()
            if n and n not in seen and len(n) <= 64:
                seen.add(n)
                cleaned.append(n)
        return cleaned


class SpiceRouteOwner(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str


class SpiceRouteSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    prep_minutes: int
    cook_minutes: int
    servings: int
    image_url: str | None
    is_public: bool
    cuisine: Cuisine | None
    language: str
    spice_level: int
    is_premium: bool
    calories_per_serving: int | None = None
    owner: SpiceRouteOwner | None = None
    tags: list[TagOut]


class SpiceRouteDetail(SpiceRouteSummary):
    ingredients: list[IngredientOut]
    steps: list[StepOut]


class SpiceRouteListResponse(BaseModel):
    items: list[SpiceRouteSummary]
    total: int
    limit: int
    offset: int
