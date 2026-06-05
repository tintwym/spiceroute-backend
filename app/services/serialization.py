from uuid import UUID

from app.core.config import get_settings
from app.models.spice_route import SpiceRoute
from app.schemas.spice_route import (
    IngredientOut,
    SpiceRouteDetail,
    SpiceRouteOwner,
    SpiceRouteSummary,
    StepOut,
    TagOut,
)

settings = get_settings()


def image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return f"{settings.public_image_base_url.rstrip('/')}/{image_path}"


def to_summary(
    spice_route: SpiceRoute,
    *,
    owner_display_name: str,
    favorite_ids: set[UUID] | None = None,
) -> SpiceRouteSummary:
    return SpiceRouteSummary(
        id=spice_route.id,
        title=spice_route.title,
        description=spice_route.description,
        prep_minutes=spice_route.prep_minutes,
        cook_minutes=spice_route.cook_minutes,
        servings=spice_route.servings,
        image_url=image_url(spice_route.image_path),
        is_public=spice_route.is_public,
        owner=SpiceRouteOwner(id=spice_route.user_id, display_name=owner_display_name),
        tags=[TagOut.model_validate(t) for t in spice_route.tags],
        is_favorite=bool(favorite_ids and spice_route.id in favorite_ids),
    )


def to_detail(
    spice_route: SpiceRoute,
    *,
    owner_display_name: str,
    favorite_ids: set[UUID] | None = None,
) -> SpiceRouteDetail:
    summary = to_summary(
        spice_route,
        owner_display_name=owner_display_name,
        favorite_ids=favorite_ids,
    )
    return SpiceRouteDetail(
        **summary.model_dump(),
        ingredients=[IngredientOut.model_validate(i) for i in spice_route.ingredients],
        steps=[StepOut.model_validate(s) for s in spice_route.steps],
    )
