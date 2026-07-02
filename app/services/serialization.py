from app.models.cuisine_catalog import cuisine_for_display
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
        cuisine=(
            cuisine_for_display(spice_route.cuisine)
            if spice_route.cuisine is not None
            else None
        ),
        language=spice_route.language,
        spice_level=spice_route.spice_level,
        is_premium=spice_route.is_premium,
        calories_per_serving=spice_route.calories_per_serving,
        difficulty=spice_route.difficulty,
        owner=owner,
        tags=[TagOut.model_validate(t) for t in spice_route.tags],
    )


def to_detail(
    spice_route: SpiceRoute,
    *,
    owner_display_name: str | None = None,
    title_override: str | None = None,
    description_override: str | None = None,
    ingredients_override: list[str] | None = None,
    steps_override: list[str] | None = None,
) -> SpiceRouteDetail:
    """Serialise an ORM row to the public detail shape.

    `ingredients_override` / `steps_override`, when present, swap the
    `name` of each ingredient row and the `body` of each step row
    with their already-localised translation. The override lists MUST
    be the same length as the source collections; the caller
    (`spice_routes.py::_resolve_translation`) enforces this on the
    way in and returns `None` on mismatch. We assert here as a final
    safety net so a programmer error can't render a wrong-row body
    under the wrong step number.

    Quantity / unit are NOT swapped — they're either numeric or
    universal-enough abbreviations ("ml", "g") that already read
    correctly in every locale. If a translator needed to localise
    "tbsp" → "muỗng canh" they would have folded that into the
    composed name string at translate-time
    (see `format_ingredient_line` on the backend).
    """
    summary = to_summary(
        spice_route,
        owner_display_name=owner_display_name,
        title_override=title_override,
        description_override=description_override,
    )

    src_ingredients = spice_route.ingredients
    src_steps = spice_route.steps

    if (
        ingredients_override is not None
        and len(ingredients_override) != len(src_ingredients)
    ):
        # Should be impossible — _resolve_translation guarantees
        # equal length or returns None — but defend rather than
        # render misaligned rows.
        ingredients_override = None
    if steps_override is not None and len(steps_override) != len(src_steps):
        steps_override = None

    ingredients_out: list[IngredientOut] = []
    for idx, i in enumerate(src_ingredients):
        ing = IngredientOut.model_validate(i)
        if ingredients_override is not None:
            # When a translated line is present it carries the WHOLE
            # composed phrase (qty + unit + name in idiomatic order
            # for the target language). Render path joins these
            # fields with spaces, so blank out qty/unit to avoid
            # double-rendering ("1 thumb 1 thumb fresh ginger").
            ing = ing.model_copy(update={
                "quantity": None,
                "unit": None,
                "name": ingredients_override[idx],
            })
        ingredients_out.append(ing)

    steps_out: list[StepOut] = []
    for idx, s in enumerate(src_steps):
        step = StepOut.model_validate(s)
        if steps_override is not None:
            step = step.model_copy(update={"body": steps_override[idx]})
        steps_out.append(step)

    return SpiceRouteDetail(
        **summary.model_dump(),
        ingredients=ingredients_out,
        steps=steps_out,
    )
