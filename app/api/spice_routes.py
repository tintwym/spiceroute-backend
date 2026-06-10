from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, OptionalCurrentUser
from app.models.cuisine import Cuisine
from app.models.spice_route import SpiceRoute
from app.models.tag import Tag
from app.models.user import User
from app.schemas.spice_route import (
    SpiceRouteCreate,
    SpiceRouteDetail,
    SpiceRouteListResponse,
    SpiceRouteUpdate,
)
from app.services.serialization import to_detail, to_summary
from app.services.spice_routes import build_ingredients, build_steps, upsert_tags

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
    q: str | None = None,
    cuisine: Cuisine | None = None,
    language: str | None = Query(default=None, max_length=8),
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
) -> SpiceRouteListResponse:
    """List recipes.

    Default visibility is "public only". Two opt-ins for authenticated callers:

      * `mine=true`           → only the caller's own recipes (incl. private)
      * (no flag, just authed) → public + caller's own private recipes

    Filters:
        q             title / description / ingredient name substring
        cuisine       one of the 16 supported cuisines
        language      one of en, zh, my, ja, ko, vi
        tag           free-form tag exact match
        max_minutes   prep + cook upper bound
        premium_only  only the curated seed set
    """
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

    if cuisine is not None:
        stmt = stmt.where(SpiceRoute.cuisine == cuisine)
        count_stmt = count_stmt.where(SpiceRoute.cuisine == cuisine)

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

    # Stable sort: the seed script writes the 27 curated `is_premium`
    # rows in a tight loop, so several share `created_at` to the
    # millisecond. Without a tiebreaker, Postgres is free to return
    # ties in any order — meaning the same recipe can show up on
    # both page 1 and page 2 of `?offset=20`, or vanish from both.
    # Sorting on `id` (UUID) as the final tiebreaker gives every
    # request the same total ordering.
    stmt = (
        stmt.order_by(
            SpiceRoute.is_premium.desc(),
            SpiceRoute.created_at.desc(),
            SpiceRoute.id,
        )
        .limit(limit)
        .offset(offset)
    )
    spice_routes = (await db.scalars(stmt)).unique().all()

    owner_names = await _load_owner_names(
        db, {r.user_id for r in spice_routes if r.user_id is not None}
    )

    items = [
        to_summary(
            r,
            owner_display_name=owner_names.get(r.user_id) if r.user_id else None,
        )
        for r in spice_routes
    ]
    return SpiceRouteListResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.post(
    "", response_model=SpiceRouteDetail, status_code=status.HTTP_201_CREATED
)
async def create_spice_route(
    payload: SpiceRouteCreate, db: DbSession, user: CurrentUser
) -> SpiceRouteDetail:
    """Create a new recipe attributed to the authenticated caller.

    Note: `is_premium` is ignored on input — only the curated seed set is
    premium and that's controlled by the seed script, not user input.
    """
    tags = await upsert_tags(db, payload.tags)
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
        image_path=payload.image_url,
        ingredients=build_ingredients(payload.ingredients),
        steps=build_steps(payload.steps),
        tags=tags,
    )
    db.add(spice_route)
    await db.commit()
    await db.refresh(spice_route)
    return to_detail(spice_route, owner_display_name=user.display_name)


@router.get("/{spice_route_id}", response_model=SpiceRouteDetail)
async def get_spice_route(
    spice_route_id: UUID,
    db: DbSession,
    user: OptionalCurrentUser = None,
) -> SpiceRouteDetail:
    spice_route = await db.get(SpiceRoute, spice_route_id)
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
    return to_detail(
        spice_route,
        owner_display_name=(
            owner_names.get(spice_route.user_id)
            if spice_route.user_id
            else None
        ),
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

    data = payload.model_dump(exclude_unset=True)

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
