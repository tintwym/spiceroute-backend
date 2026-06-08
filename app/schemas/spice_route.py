from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.cuisine import Cuisine

NameStr = Annotated[str, Field(min_length=1, max_length=200)]
SUPPORTED_LANGUAGES = ("en", "zh", "th", "ja", "ko", "vi")


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
