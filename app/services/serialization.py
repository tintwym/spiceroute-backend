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
    title_override: str | None = None,
    description_override: str | None = None,
) -> SpiceRouteSummary:
    """Serialise an ORM row to the public summary shape.

    `title_override` / `description_override` let callers substitute a
    per-locale translated value WITHOUT touching the ORM instance. We
    used to swap `spice_route.title` in place before serialising — that
    works today (read endpoints don't commit) but it's a silent
    foot-gun: any future code path that calls `db.commit()` on the same
    session (or any middleware that does an implicit commit) would
    persist the translated string back into `spice_routes.title`,
    permanently corrupting the source data. Threading the overrides
    through the serializer keeps the ORM row read-only and makes the
    translation contract explicit at every call site.

    A `None` override means "use the row's value as-is". Empty strings
    are intentionally NOT treated as "no override" — that's the
    caller's job to police, because there might be a legitimate use
    case for blanking out a description (we don't have one today but
    we'd rather not silently swallow the intent).
    """
    owner = (
        SpiceRouteOwner(id=spice_route.user_id, display_name=owner_display_name)
        if spice_route.user_id and owner_display_name is not None
        else None
    )
    return SpiceRouteSummary(
        id=spice_route.id,
        title=title_override if title_override is not None else spice_route.title,
        description=(
            description_override
            if description_override is not None
            else spice_route.description
        ),
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
    title_override: str | None = None,
    description_override: str | None = None,
) -> SpiceRouteDetail:
    summary = to_summary(
        spice_route,
        owner_display_name=owner_display_name,
        title_override=title_override,
        description_override=description_override,
    )
    return SpiceRouteDetail(
        **summary.model_dump(),
        ingredients=[IngredientOut.model_validate(i) for i in spice_route.ingredients],
        steps=[StepOut.model_validate(s) for s in spice_route.steps],
    )
