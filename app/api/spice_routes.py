from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.models.favorite import Favorite
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


async def _load_owner_names(db: DbSession, user_ids: set[UUID]) -> dict[UUID, str]:
    if not user_ids:
        return {}
    rows = await db.execute(
        select(User.id, User.display_name).where(User.id.in_(user_ids))
    )
    return {row.id: row.display_name for row in rows}


async def _load_favorite_ids(
    db: DbSession, user: User | None, spice_route_ids: list[UUID]
) -> set[UUID]:
    if not user or not spice_route_ids:
        return set()
    rows = await db.scalars(
        select(Favorite.spice_route_id).where(
            Favorite.user_id == user.id,
            Favorite.spice_route_id.in_(spice_route_ids),
        )
    )
    return set(rows)


def _ensure_visible(spice_route: SpiceRoute, user: User | None) -> None:
    if spice_route.is_public:
        return
    if user and spice_route.user_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="spice_route not found")


def _ensure_owner(spice_route: SpiceRoute, user: User) -> None:
    if spice_route.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not the spice_route owner"
        )


@router.get("", response_model=SpiceRouteListResponse)
async def list_spice_routes(
    db: DbSession,
    user: OptionalUser,
    q: str | None = None,
    tag: str | None = None,
    max_minutes: int | None = Query(default=None, ge=0),
    mine_only: bool = False,
    favorites_only: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SpiceRouteListResponse:
    stmt = select(SpiceRoute).options(selectinload(SpiceRoute.tags))
    count_stmt = select(func.count(SpiceRoute.id))

    visibility = SpiceRoute.is_public.is_(True)
    if user:
        visibility = or_(visibility, SpiceRoute.user_id == user.id)
    stmt = stmt.where(visibility)
    count_stmt = count_stmt.where(visibility)

    if mine_only:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="login required for mine_only",
            )
        stmt = stmt.where(SpiceRoute.user_id == user.id)
        count_stmt = count_stmt.where(SpiceRoute.user_id == user.id)

    if favorites_only:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="login required for favorites_only",
            )
        fav_subq = select(Favorite.spice_route_id).where(Favorite.user_id == user.id)
        stmt = stmt.where(SpiceRoute.id.in_(fav_subq))
        count_stmt = count_stmt.where(SpiceRoute.id.in_(fav_subq))

    if max_minutes is not None:
        stmt = stmt.where((SpiceRoute.prep_minutes + SpiceRoute.cook_minutes) <= max_minutes)
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
        ingredient_match = select(_Ing.spice_route_id).where(func.lower(_Ing.name).like(like))
        search_clause = or_(
            func.lower(SpiceRoute.title).like(like),
            func.lower(SpiceRoute.description).like(like),
            SpiceRoute.id.in_(ingredient_match),
        )
        stmt = stmt.where(search_clause)
        count_stmt = count_stmt.where(search_clause)

    total = (await db.scalar(count_stmt)) or 0

    stmt = stmt.order_by(SpiceRoute.created_at.desc()).limit(limit).offset(offset)
    spice_routes = (await db.scalars(stmt)).unique().all()

    owner_names = await _load_owner_names(db, {r.user_id for r in spice_routes})
    favorite_ids = await _load_favorite_ids(db, user, [r.id for r in spice_routes])

    items = [
        to_summary(
            r,
            owner_display_name=owner_names.get(r.user_id, ""),
            favorite_ids=favorite_ids,
        )
        for r in spice_routes
    ]
    return SpiceRouteListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=SpiceRouteDetail, status_code=status.HTTP_201_CREATED)
async def create_spice_route(
    payload: SpiceRouteCreate, db: DbSession, user: CurrentUser
) -> SpiceRouteDetail:
    tags = await upsert_tags(db, payload.tags)
    spice_route = SpiceRoute(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        prep_minutes=payload.prep_minutes,
        cook_minutes=payload.cook_minutes,
        servings=payload.servings,
        is_public=payload.is_public,
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
    spice_route_id: UUID, db: DbSession, user: OptionalUser
) -> SpiceRouteDetail:
    spice_route = await db.get(SpiceRoute, spice_route_id)
    if not spice_route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="spice_route not found")
    _ensure_visible(spice_route, user)
    owner_names = await _load_owner_names(db, {spice_route.user_id})
    favorite_ids = await _load_favorite_ids(db, user, [spice_route.id])
    return to_detail(
        spice_route,
        owner_display_name=owner_names.get(spice_route.user_id, ""),
        favorite_ids=favorite_ids,
    )


@router.patch("/{spice_route_id}", response_model=SpiceRouteDetail)
async def update_spice_route(
    spice_route_id: UUID,
    payload: SpiceRouteUpdate,
    db: DbSession,
    user: CurrentUser,
) -> SpiceRouteDetail:
    spice_route = await db.get(SpiceRoute, spice_route_id)
    if not spice_route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="spice_route not found")
    _ensure_owner(spice_route, user)

    data = payload.model_dump(exclude_unset=True)
    for field in ("title", "description", "prep_minutes", "cook_minutes", "servings", "is_public"):
        if field in data:
            setattr(spice_route, field, data[field])

    if payload.ingredients is not None:
        spice_route.ingredients = build_ingredients(payload.ingredients)
    if payload.steps is not None:
        spice_route.steps = build_steps(payload.steps)
    if payload.tags is not None:
        spice_route.tags = await upsert_tags(db, payload.tags)

    await db.commit()
    await db.refresh(spice_route)
    return to_detail(spice_route, owner_display_name=user.display_name)


@router.delete("/{spice_route_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_spice_route(
    spice_route_id: UUID, db: DbSession, user: CurrentUser
) -> Response:
    spice_route = await db.get(SpiceRoute, spice_route_id)
    if not spice_route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="spice_route not found")
    _ensure_owner(spice_route, user)
    await db.delete(spice_route)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
