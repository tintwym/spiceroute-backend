from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import ClientIP, CurrentUser, DbSession, OptionalCurrentUser
from app.models.cuisine import Cuisine
from app.models.cuisine_catalog import cuisine_filter_values
from app.models.difficulty import compute_difficulty
from app.models.spice_route import SpiceRoute
from app.models.tag import Tag
from app.models.user import User
from app.schemas.spice_route import (
    SpiceRouteCreate,
    SpiceRouteDetail,
    SpiceRouteListResponse,
    SpiceRouteUpdate,
)
from app.services.ai import llm, rate_limit
from app.services.locale_request import requested_translation_locale
from app.services.recipe_translations import (
    ensure_row_translations,
    source_ingredient_lines,
    source_step_lines,
)
from app.services.serialization import to_detail, to_summary
from app.services.spice_routes import (
    build_ingredients,
    build_steps,
    format_ingredient_line,
    upsert_tags,
)
from scripts.translation_utils import (
    is_garbage_translation_text,
    is_stub_description_value,
    is_stub_title_value,
)

router = APIRouter()


async def _load_owner_names(
    db: DbSession, user_ids: set[UUID]
) -> dict[UUID, str]:
    if not user_ids:
        return {}
    rows = await db.execute(
        select(User.id, User.display_name).where(User.id.in_(user_ids))
    )
    return {row.id: row.display_name for row in rows}


def _resolve_translation(
    row: SpiceRoute,
    locale: str | None,
    *,
    summary_only: bool = False,
) -> tuple[str | None, str | None, list[str] | None, list[str] | None]:
    """Look up the per-locale overrides for a row, returning
    `(title_override, description_override, ingredients_override,
    steps_override)` for the serializer. `None` means "no override —
    fall back to the row's source-of-truth column" (see `to_summary`
    docstring).

    The two list overrides are only meaningful for the detail
    serializer; the summary path ignores them. They MUST be the same
    length as the row's `ingredients` / `steps` collections — the
    LLM-translate path enforces this on the way in (`llm.py::
    translate_recipe_content`) and we re-enforce it on the read side
    as defence in depth: a malformed length would misalign step bodies
    against their numbered cards, which is much worse than no
    translation.

    Why this is read-only (no ORM mutation): the older shape of this
    helper wrote `row.title = translated_title` directly. That worked
    only because our read endpoints don't commit, but SQLAlchemy still
    flagged the attribute as dirty. Any later code path that triggered
    a commit on the same session (a future write endpoint sharing the
    session, a middleware, or just someone adding `await db.commit()`
    here without realising) would have silently persisted the
    translated string back into `spice_routes.title`, irreversibly
    corrupting the seed data. Returning override values instead keeps
    the ORM instance untouched and makes the translation flow explicit
    at the call site.

    Returns `(None, None)` when:
      - `locale` is null / empty (caller didn't request a translation)
      - the row's `translations` column is null / empty (no locale
        overrides were seeded for this recipe)
      - `translations[locale]` doesn't exist (no override for the
        specific locale the caller asked for)
      - the row's `translations` column or its `[locale]` entry is
        present but not the expected dict shape (e.g. a list got
        written by a buggy migration / future writer). We refuse to
        crash on shape drift — there are no current writers that can
        produce this, but `/spice_routes?translate_to=…` is the most
        widely-hit endpoint in the app and a 500 here takes Explore
        down for every authenticated client. Defensive type guards
        are cheaper than the alternative.

    For a partial override (e.g. a locale entry that supplies only a
    description because the dish has no settled title transliteration
    in that language), the missing field is returned as `None` so the
    serializer falls back to the source column for just that one
    field — preventing blank titles on the UI.
    """
    if not locale:
        return None, None, None, None
    translations = row.translations
    # Belt-and-braces: model types this as `dict | None`, but the
    # underlying JSONB column will faithfully return whatever JSON
    # value got stored. A buggy writer (or a hand-crafted UPDATE in
    # psql) could plant a list, string, or int here. `.get()` on
    # any non-dict value raises AttributeError, which would 500 the
    # listing endpoint with no useful client recovery path.
    if not isinstance(translations, dict):
        return None, None, None, None
    bundle = translations.get(locale)
    if not isinstance(bundle, dict):
        return None, None, None, None
    raw_title = bundle.get("title")
    raw_description = bundle.get("description")
    raw_ingredients = bundle.get("ingredients")
    raw_steps = bundle.get("steps")
    # Coerce non-string values (numbers, bools, nested dicts) to None
    # so the serializer's `str` type doesn't see something it can't
    # render. Empty strings also collapse to None so the source-row
    # fallback kicks in instead of painting a blank title.
    translated_title = raw_title if isinstance(raw_title, str) and raw_title else None
    translated_description = (
        raw_description
        if isinstance(raw_description, str) and raw_description
        else None
    )
    # Expansion seeds used to copy English into locale bundles. Drop
    # only the fields that are still English — keep real partial
    # overrides (e.g. description-only bundles in curated seeds).
    if translated_title is not None and is_stub_title_value(
        translated_title, row.title
    ):
        translated_title = None
    if translated_description is not None and is_stub_description_value(
        translated_description, row.description
    ):
        translated_description = None
    # LLM backfills occasionally produce repetitive garbage strings.
    # Fall back to the source column rather than painting nonsense on
    # Explore cards (e.g. zh descriptions that are just repeated chars).
    if translated_title is not None and is_garbage_translation_text(
        translated_title, field="title"
    ):
        translated_title = None
    if translated_description is not None and is_garbage_translation_text(
        translated_description, field="description"
    ):
        translated_description = None
    if summary_only:
        return translated_title, translated_description, None, None
    # Lists: keep only if length matches the source collection, every
    # element is a non-empty string, and the row's collection has
    # been loaded (selectin in the model means it always is for
    # detail/summary paths, but guard anyway so a partial load can't
    # silently misalign). Length mismatch falls back to per-row
    # source strings (resolver returns None).
    def _coerce_list(
        raw, source_count: int
    ) -> list[str] | None:
        if (
            not isinstance(raw, list)
            or len(raw) != source_count
            or source_count == 0
        ):
            return None
        out: list[str] = []
        for item in raw:
            if not isinstance(item, str) or not item.strip():
                return None
            out.append(item)
        return out

    translated_ingredients = _coerce_list(
        raw_ingredients, len(row.ingredients)
    )
    translated_steps = _coerce_list(raw_steps, len(row.steps))
    src_ings = source_ingredient_lines(row)
    src_steps = source_step_lines(row)
    if translated_ingredients is not None and translated_ingredients == src_ings:
        translated_ingredients = None
    if translated_steps is not None and translated_steps == src_steps:
        translated_steps = None
    return (
        translated_title,
        translated_description,
        translated_ingredients,
        translated_steps,
    )


async def _get_owned_recipe(
    db: DbSession, spice_route_id: UUID, user: User
) -> SpiceRoute:
    """Fetch a recipe and verify the caller owns it. 404s on either failure
    (we deliberately don't reveal "exists but not yours" — that's a low-key
    enumeration vector)."""
    spice_route = await db.get(SpiceRoute, spice_route_id)
    if spice_route is None or spice_route.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="recipe not found"
        )
    return spice_route


@router.get("", response_model=SpiceRouteListResponse)
async def list_spice_routes(
    db: DbSession,
    ip: ClientIP,
    q: str | None = None,
    cuisine: Cuisine | None = None,
    language: str | None = Query(default=None, max_length=8),
    translate_to: str | None = Query(
        default=None,
        max_length=8,
        description="Locale to translate title/description into when a "
        "matching entry exists in the recipe's translations bundle. "
        "Distinct from `language` (which filters by the recipe's *source* "
        "language). Missing translations fall back silently to the source "
        "title/description, so callers can pass this on every request.",
    ),
    tag: str | None = None,
    max_minutes: int | None = Query(default=None, ge=0),
    premium_only: bool = False,
    mine: bool = Query(
        default=False,
        description="If true and authenticated, returns only the caller's "
        "recipes (including private ones).",
    ),
    user: OptionalCurrentUser = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> SpiceRouteListResponse:
    """List recipes.

    Default visibility is "public only". Two opt-ins for authenticated callers:

      * `mine=true`           → only the caller's own recipes (incl. private)
      * (no flag, just authed) → public + caller's own private recipes

    Filters:
        q             title / description / ingredient name substring
        cuisine       one of the 31 supported cuisines
        language      one of en, zh, ja, ko, vi      (filters by source)
        translate_to  same set, but switches title/description to the
                      per-locale override when one was seeded for the row
                      (no filter, no fallback to empty)
        tag           free-form tag exact match
        max_minutes   prep + cook upper bound
        premium_only  only the curated seed set
    """
    # Throttle BEFORE we touch the rest of the request. Over-quota
    # requests then cost one INSERT/UPDATE on the counter table and
    # zero work against the (much heavier) recipe + tag joins below.
    # See `app/services/ai/rate_limit.py::check_recipe_list_quota`
    # for the ceiling and rationale.
    await rate_limit.check_recipe_list_quota(db, ip=ip)

    stmt = select(SpiceRoute).options(selectinload(SpiceRoute.tags))
    count_stmt = select(func.count(SpiceRoute.id))

    if mine:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="`mine=true` requires authentication",
            )
        visibility = SpiceRoute.user_id == user.id
    elif user is not None:
        visibility = or_(
            SpiceRoute.is_public.is_(True),
            SpiceRoute.user_id == user.id,
        )
    else:
        visibility = SpiceRoute.is_public.is_(True)

    stmt = stmt.where(visibility)
    count_stmt = count_stmt.where(visibility)

    # Eastern European was dropped from the curated catalog but rows can
    # linger in prod until re-seed. Hide them from the public list rather
    # than 500ing when the sort order surfaces a legacy row.
    retired_cuisines = (Cuisine.EASTERN_EUROPEAN,)
    stmt = stmt.where(
        or_(
            SpiceRoute.cuisine.is_(None),
            SpiceRoute.cuisine.not_in(retired_cuisines),
        )
    )
    count_stmt = count_stmt.where(
        or_(
            SpiceRoute.cuisine.is_(None),
            SpiceRoute.cuisine.not_in(retired_cuisines),
        )
    )

    if cuisine is not None:
        cuisine_values = cuisine_filter_values(cuisine)
        if cuisine_values is not None and len(cuisine_values) == 1:
            stmt = stmt.where(SpiceRoute.cuisine == cuisine_values[0])
            count_stmt = count_stmt.where(SpiceRoute.cuisine == cuisine_values[0])
        elif cuisine_values:
            stmt = stmt.where(SpiceRoute.cuisine.in_(cuisine_values))
            count_stmt = count_stmt.where(SpiceRoute.cuisine.in_(cuisine_values))

    if language:
        lang = language.strip().lower()
        stmt = stmt.where(SpiceRoute.language == lang)
        count_stmt = count_stmt.where(SpiceRoute.language == lang)

    if premium_only:
        stmt = stmt.where(SpiceRoute.is_premium.is_(True))
        count_stmt = count_stmt.where(SpiceRoute.is_premium.is_(True))

    if max_minutes is not None:
        stmt = stmt.where(
            (SpiceRoute.prep_minutes + SpiceRoute.cook_minutes) <= max_minutes
        )
        count_stmt = count_stmt.where(
            (SpiceRoute.prep_minutes + SpiceRoute.cook_minutes) <= max_minutes
        )

    if tag:
        tag_clean = tag.strip().lower()
        stmt = stmt.where(SpiceRoute.tags.any(Tag.name == tag_clean))
        count_stmt = count_stmt.where(SpiceRoute.tags.any(Tag.name == tag_clean))

    if q:
        from app.models.spice_route import Ingredient as _Ing

        like = f"%{q.lower()}%"
        ingredient_match = select(_Ing.spice_route_id).where(
            func.lower(_Ing.name).like(like)
        )
        search_clause = or_(
            func.lower(SpiceRoute.title).like(like),
            func.lower(SpiceRoute.description).like(like),
            SpiceRoute.id.in_(ingredient_match),
        )
        stmt = stmt.where(search_clause)
        count_stmt = count_stmt.where(search_clause)

    total = (await db.scalar(count_stmt)) or 0

    # Stable sort: premium rows first, then a cuisine-mixed order.
    #
    # `created_at desc` grouped the explore grid by seed batch — the
    # Myanmar expansion landed last, so Burmese recipes monopolised
    # page 1 before any other cuisine appeared. UUID lexical order is
    # stable across pages (no duplicate/vanishing rows on offset
    # pagination) and pseudo-random across cuisines, so the default
    # "All cuisines" view reads as a mixed catalog instead of a
    # newest-batch-first pile.
    stmt = (
        stmt.order_by(
            SpiceRoute.is_premium.desc(),
            SpiceRoute.id,
        )
        .limit(limit)
        .offset(offset)
    )
    spice_routes = (await db.scalars(stmt)).unique().all()

    owner_names = await _load_owner_names(
        db, {r.user_id for r in spice_routes if r.user_id is not None}
    )

    # Resolve per-locale title/description overrides BEFORE
    # serialisation. We pass them as kwargs into `to_summary` so the
    # raw `translations` JSONB blob never leaks into the wire format
    # and the ORM rows stay read-only — see `_resolve_translation`
    # docstring for the rationale.
    requested_locale = requested_translation_locale(
        translate_to=translate_to,
        accept_language=accept_language,
    )
    items = []
    for r in spice_routes:
        # Summary path only consumes the title + description overrides;
        # the list/grid card doesn't render ingredients or steps. The
        # ingredients/steps overrides are unpacked into `_` so the
        # return-shape change is explicit at the call site rather than
        # quietly swallowed by tuple unpacking.
        title_override, desc_override, _, _ = _resolve_translation(
            r, requested_locale, summary_only=True
        )
        items.append(
            to_summary(
                r,
                owner_display_name=(
                    owner_names.get(r.user_id) if r.user_id else None
                ),
                title_override=title_override,
                description_override=desc_override,
            )
        )
    return SpiceRouteListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.post(
    "", response_model=SpiceRouteDetail, status_code=status.HTTP_201_CREATED
)
async def create_spice_route(
    payload: SpiceRouteCreate,
    db: DbSession,
    user: CurrentUser,
    ip: ClientIP,
) -> SpiceRouteDetail:
    """Create a new recipe attributed to the authenticated caller.

    Note: `is_premium` is ignored on input — only the curated seed set is
    premium and that's controlled by the seed script, not user input.
    """
    # Throttle BEFORE doing any work (tag upsert, translation LLM call,
    # etc.). Auth already gates anonymous abuse; this layer protects
    # against a single attacker creating many accounts behind one IP
    # and spam-publishing. Default ceiling is 50/day — see
    # `check_recipe_write_quota` for the rationale.
    await rate_limit.check_recipe_write_quota(db, ip=ip)
    tags = await upsert_tags(db, payload.tags)
    # Best-effort save-time translation of title + description +
    # ingredients + steps into every supported locale other than the
    # source. Without this the recipe ships with `translations` NULL
    # and any user whose UI locale != source language sees the
    # source-language string for every field. The helper returns
    # None (not raises) on any LLM failure, so a flaky provider can
    # never block a user from saving their own content — see
    # `translate_recipe_content` docstring for the full failure
    # contract (including per-field drop on length mismatch).
    translations = await llm.translate_recipe_content(
        title=payload.title,
        description=payload.description,
        source_language=payload.language,
        ingredients=[
            format_ingredient_line(
                quantity=i.quantity, unit=i.unit, name=i.name
            )
            for i in payload.ingredients
        ],
        steps=[s.body for s in payload.steps],
    )
    # Auto-compute difficulty when the client didn't pin one. This is
    # what keeps the `difficulty` column uniformly populated across
    # the table — without it, untrusted clients could omit the field
    # and the DB would silently fall back to the `medium` server
    # default (defeating the whole point of having a derived value).
    # `compute_difficulty` is pure and never raises.
    difficulty = payload.difficulty or compute_difficulty(
        prep_minutes=payload.prep_minutes,
        cook_minutes=payload.cook_minutes,
        step_count=len(payload.steps),
    )
    spice_route = SpiceRoute(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        prep_minutes=payload.prep_minutes,
        cook_minutes=payload.cook_minutes,
        servings=payload.servings,
        is_public=payload.is_public,
        cuisine=payload.cuisine,
        language=payload.language,
        spice_level=payload.spice_level,
        is_premium=False,
        calories_per_serving=payload.calories_per_serving,
        difficulty=difficulty,
        image_path=payload.image_url,
        ingredients=build_ingredients(payload.ingredients),
        steps=build_steps(payload.steps),
        tags=tags,
        translations=translations,
    )
    db.add(spice_route)
    await db.commit()
    await db.refresh(spice_route)
    return to_detail(spice_route, owner_display_name=user.display_name)


@router.get("/{spice_route_id}", response_model=SpiceRouteDetail)
async def get_spice_route(
    spice_route_id: UUID,
    db: DbSession,
    ip: ClientIP,
    user: OptionalCurrentUser = None,
    translate_to: str | None = Query(
        default=None,
        max_length=8,
        description="Locale to translate title/description into when a "
        "matching entry exists in the recipe's translations bundle. See "
        "list_spice_routes for the full contract.",
    ),
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> SpiceRouteDetail:
    # Throttle before the lookup — same reasoning as `list_spice_routes`.
    # Detail fetches use a heavier cap (default 600/hr) because they're
    # the natural follow-up to a list call.
    await rate_limit.check_recipe_detail_quota(db, ip=ip)
    stmt = (
        select(SpiceRoute)
        .options(
            selectinload(SpiceRoute.ingredients),
            selectinload(SpiceRoute.steps),
        )
        .where(SpiceRoute.id == spice_route_id)
    )
    spice_route = (await db.scalars(stmt)).first()
    if not spice_route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="recipe not found"
        )

    is_owner = user is not None and spice_route.user_id == user.id
    if not spice_route.is_public and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="recipe not found"
        )

    owner_names = await _load_owner_names(
        db, {spice_route.user_id} if spice_route.user_id else set()
    )
    requested_locale = requested_translation_locale(
        translate_to=translate_to,
        accept_language=accept_language,
    )
    if (
        requested_locale
        and requested_locale != (spice_route.language or "en").lower()
    ):
        # First open in a new UI locale: LLM-fill + persist so Explore
        # cards pick up the translation on the next list refresh too.
        await ensure_row_translations(db, spice_route)
    (
        title_override,
        desc_override,
        ingredients_override,
        steps_override,
    ) = _resolve_translation(spice_route, requested_locale)
    return to_detail(
        spice_route,
        owner_display_name=(
            owner_names.get(spice_route.user_id)
            if spice_route.user_id
            else None
        ),
        title_override=title_override,
        description_override=desc_override,
        ingredients_override=ingredients_override,
        steps_override=steps_override,
    )


@router.patch(
    "/{spice_route_id}", response_model=SpiceRouteDetail
)
async def update_spice_route(
    spice_route_id: UUID,
    payload: SpiceRouteUpdate,
    db: DbSession,
    user: CurrentUser,
) -> SpiceRouteDetail:
    """Owner-only partial update."""
    spice_route = await _get_owned_recipe(db, spice_route_id, user)

    # `provided` is the set of fields the caller actually sent (vs.
    # left unset). Captured BEFORE we start popping keys out of `data`
    # so the difficulty / translation re-derivation blocks below can
    # still ask "did the caller touch X in this request" without
    # rebuilding the dump.
    data = payload.model_dump(exclude_unset=True)
    provided = set(data)

    # Map schema -> column where they differ.
    if "image_url" in data:
        spice_route.image_path = data.pop("image_url")
    if "ingredients" in data:
        spice_route.ingredients = build_ingredients(payload.ingredients or [])
        data.pop("ingredients")
    if "steps" in data:
        spice_route.steps = build_steps(payload.steps or [])
        data.pop("steps")
    if "tags" in data:
        spice_route.tags = await upsert_tags(db, payload.tags or [])
        data.pop("tags")

    for field, value in data.items():
        setattr(spice_route, field, value)

    # Re-translate if ANY translated field (or the source language)
    # changed — otherwise the JSONB still points at the OLD title /
    # ingredient list / steps for non-source UI locales and a
    # Vietnamese viewer would see the user's edits in English but
    # stale Vietnamese content from before the edit, which is more
    # confusing than no translation at all. Reading from `provided`
    # (which captures the unset-vs-explicit distinction at the start
    # of the handler) so a PATCH that only touches `tags` doesn't
    # trigger a needless LLM call. If translation fails we clear the
    # column to NULL rather than leaving stale entries — the
    # resolver's fallback to the source string is the safer default.
    if provided & {
        "title", "description", "language", "ingredients", "steps"
    }:
        spice_route.translations = await llm.translate_recipe_content(
            title=spice_route.title,
            description=spice_route.description,
            source_language=spice_route.language,
            ingredients=[
                format_ingredient_line(
                    quantity=i.quantity, unit=i.unit, name=i.name
                )
                for i in spice_route.ingredients
            ],
            steps=[s.body for s in spice_route.steps],
        )

    # Re-derive difficulty when any input that feeds the rule changes
    # AND the caller didn't pin an explicit override in this PATCH.
    # Reading the (already-mutated) ORM row instead of `data` so the
    # newly-attached steps relationship is what we measure, not the
    # raw input payload. Skip when the user explicitly pinned a value
    # in this request — that takes precedence over the auto-rule.
    auto_inputs_changed = bool(
        provided & {"prep_minutes", "cook_minutes", "steps"}
    )
    if "difficulty" not in provided and auto_inputs_changed:
        spice_route.difficulty = compute_difficulty(
            prep_minutes=spice_route.prep_minutes,
            cook_minutes=spice_route.cook_minutes,
            step_count=len(spice_route.steps),
        )

    await db.commit()
    await db.refresh(spice_route)
    return to_detail(spice_route, owner_display_name=user.display_name)


@router.delete(
    "/{spice_route_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_spice_route(
    spice_route_id: UUID, db: DbSession, user: CurrentUser
) -> None:
    spice_route = await _get_owned_recipe(db, spice_route_id, user)
    await db.delete(spice_route)
    await db.commit()
