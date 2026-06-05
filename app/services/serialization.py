from uuid import UUID

from app.core.config import get_settings
from app.models.mecipe import Mecipe
from app.schemas.mecipe import (
    IngredientOut,
    MecipeDetail,
    MecipeOwner,
    MecipeSummary,
    StepOut,
    TagOut,
)

settings = get_settings()


def image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return f"{settings.public_image_base_url.rstrip('/')}/{image_path}"


def to_summary(
    mecipe: Mecipe,
    *,
    owner_display_name: str,
    favorite_ids: set[UUID] | None = None,
) -> MecipeSummary:
    return MecipeSummary(
        id=mecipe.id,
        title=mecipe.title,
        description=mecipe.description,
        prep_minutes=mecipe.prep_minutes,
        cook_minutes=mecipe.cook_minutes,
        servings=mecipe.servings,
        image_url=image_url(mecipe.image_path),
        is_public=mecipe.is_public,
        owner=MecipeOwner(id=mecipe.user_id, display_name=owner_display_name),
        tags=[TagOut.model_validate(t) for t in mecipe.tags],
        is_favorite=bool(favorite_ids and mecipe.id in favorite_ids),
    )


def to_detail(
    mecipe: Mecipe,
    *,
    owner_display_name: str,
    favorite_ids: set[UUID] | None = None,
) -> MecipeDetail:
    summary = to_summary(
        mecipe,
        owner_display_name=owner_display_name,
        favorite_ids=favorite_ids,
    )
    return MecipeDetail(
        **summary.model_dump(),
        ingredients=[IngredientOut.model_validate(i) for i in mecipe.ingredients],
        steps=[StepOut.model_validate(s) for s in mecipe.steps],
    )
