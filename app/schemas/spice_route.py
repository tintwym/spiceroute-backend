from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

NameStr = Annotated[str, Field(min_length=1, max_length=200)]


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
    is_public: bool = False


class SpiceRouteCreate(SpiceRouteBase):
    ingredients: list[IngredientIn] = Field(default_factory=list, max_length=200)
    steps: list[StepIn] = Field(default_factory=list, max_length=200)
    tags: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str]) -> list[str]:
        cleaned = []
        seen = set()
        for t in v:
            n = t.strip().lower()
            if n and n not in seen and len(n) <= 64:
                seen.add(n)
                cleaned.append(n)
        return cleaned


class SpiceRouteUpdate(BaseModel):
    title: NameStr | None = None
    description: str | None = None
    prep_minutes: int | None = Field(default=None, ge=0, le=10_000)
    cook_minutes: int | None = Field(default=None, ge=0, le=10_000)
    servings: int | None = Field(default=None, ge=1, le=1000)
    is_public: bool | None = None
    ingredients: list[IngredientIn] | None = Field(default=None, max_length=200)
    steps: list[StepIn] | None = Field(default=None, max_length=200)
    tags: list[str] | None = Field(default=None, max_length=50)

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned, seen = [], set()
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
    owner: SpiceRouteOwner
    tags: list[TagOut]
    is_favorite: bool = False


class SpiceRouteDetail(SpiceRouteSummary):
    ingredients: list[IngredientOut]
    steps: list[StepOut]


class SpiceRouteListResponse(BaseModel):
    items: list[SpiceRouteSummary]
    total: int
    limit: int
    offset: int
