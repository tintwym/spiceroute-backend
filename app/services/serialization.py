from app.models.spice_route import SpiceRoute
from app.schemas.spice_route import (
    IngredientOut,
    SpiceRouteDetail,
    SpiceRouteOwner,
    SpiceRouteSummary,
    StepOut,
    TagOut,
)


def _image_url(image_path: str | None) -> str | None:
    """In zero-auth v1 we don't host user uploads — image_path stores the
    full external URL (Unsplash for curated recipes, AI-provided URL or
    NULL for AI/user recipes). This helper exists so we can later swap in
    a self-hosted CDN without touching call sites."""
    return image_path


def to_summary(
    spice_route: SpiceRoute,
    *,
    owner_display_name: str | None = None,
) -> SpiceRouteSummary:
    owner = (
        SpiceRouteOwner(id=spice_route.user_id, display_name=owner_display_name)
        if spice_route.user_id and owner_display_name is not None
        else None
    )
    return SpiceRouteSummary(
        id=spice_route.id,
        title=spice_route.title,
        description=spice_route.description,
        prep_minutes=spice_route.prep_minutes,
        cook_minutes=spice_route.cook_minutes,
        servings=spice_route.servings,
        image_url=_image_url(spice_route.image_path),
        is_public=spice_route.is_public,
        cuisine=spice_route.cuisine,
        language=spice_route.language,
        spice_level=spice_route.spice_level,
        is_premium=spice_route.is_premium,
        calories_per_serving=spice_route.calories_per_serving,
        owner=owner,
        tags=[TagOut.model_validate(t) for t in spice_route.tags],
    )


def to_detail(
    spice_route: SpiceRoute,
    *,
    owner_display_name: str | None = None,
) -> SpiceRouteDetail:
    summary = to_summary(spice_route, owner_display_name=owner_display_name)
    return SpiceRouteDetail(
        **summary.model_dump(),
        ingredients=[IngredientOut.model_validate(i) for i in spice_route.ingredients],
        steps=[StepOut.model_validate(s) for s in spice_route.steps],
    )
