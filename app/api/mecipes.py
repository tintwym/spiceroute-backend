from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession, OptionalUser
from app.models.favorite import Favorite
from app.models.mecipe import Mecipe
from app.models.tag import Tag
from app.models.user import User
from app.schemas.mecipe import (
    MecipeCreate,
    MecipeDetail,
    MecipeListResponse,
    MecipeUpdate,
)
from app.services.mecipes import build_ingredients, build_steps, upsert_tags
from app.services.serialization import to_detail, to_summary

router = APIRouter()


async def _load_owner_names(db: DbSession, user_ids: set[UUID]) -> dict[UUID, str]:
    if not user_ids:
        return {}
    rows = await db.execute(
        select(User.id, User.display_name).where(User.id.in_(user_ids))
    )
    return {row.id: row.display_name for row in rows}


async def _load_favorite_ids(
    db: DbSession, user: User | None, mecipe_ids: list[UUID]
) -> set[UUID]:
    if not user or not mecipe_ids:
        return set()
    rows = await db.scalars(
        select(Favorite.mecipe_id).where(
            Favorite.user_id == user.id,
            Favorite.mecipe_id.in_(mecipe_ids),
        )
    )
    return set(rows)


def _ensure_visible(mecipe: Mecipe, user: User | None) -> None:
    if mecipe.is_public:
        return
    if user and mecipe.user_id == user.id:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mecipe not found")


def _ensure_owner(mecipe: Mecipe, user: User) -> None:
    if mecipe.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not the mecipe owner"
        )


@router.get("", response_model=MecipeListResponse)
async def list_mecipes(
    db: DbSession,
    user: OptionalUser,
    q: str | None = None,
    tag: str | None = None,
    max_minutes: int | None = Query(default=None, ge=0),
    mine_only: bool = False,
    favorites_only: bool = False,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> MecipeListResponse:
    stmt = select(Mecipe).options(selectinload(Mecipe.tags))
    count_stmt = select(func.count(Mecipe.id))

    visibility = Mecipe.is_public.is_(True)
    if user:
        visibility = or_(visibility, Mecipe.user_id == user.id)
    stmt = stmt.where(visibility)
    count_stmt = count_stmt.where(visibility)

    if mine_only:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="login required for mine_only",
            )
        stmt = stmt.where(Mecipe.user_id == user.id)
        count_stmt = count_stmt.where(Mecipe.user_id == user.id)

    if favorites_only:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="login required for favorites_only",
            )
        fav_subq = select(Favorite.mecipe_id).where(Favorite.user_id == user.id)
        stmt = stmt.where(Mecipe.id.in_(fav_subq))
        count_stmt = count_stmt.where(Mecipe.id.in_(fav_subq))

    if max_minutes is not None:
        stmt = stmt.where((Mecipe.prep_minutes + Mecipe.cook_minutes) <= max_minutes)
        count_stmt = count_stmt.where(
            (Mecipe.prep_minutes + Mecipe.cook_minutes) <= max_minutes
        )

    if tag:
        tag_clean = tag.strip().lower()
        stmt = stmt.where(Mecipe.tags.any(Tag.name == tag_clean))
        count_stmt = count_stmt.where(Mecipe.tags.any(Tag.name == tag_clean))

    if q:
        from app.models.mecipe import Ingredient as _Ing

        like = f"%{q.lower()}%"
        ingredient_match = select(_Ing.mecipe_id).where(func.lower(_Ing.name).like(like))
        search_clause = or_(
            func.lower(Mecipe.title).like(like),
            func.lower(Mecipe.description).like(like),
            Mecipe.id.in_(ingredient_match),
        )
        stmt = stmt.where(search_clause)
        count_stmt = count_stmt.where(search_clause)

    total = (await db.scalar(count_stmt)) or 0

    stmt = stmt.order_by(Mecipe.created_at.desc()).limit(limit).offset(offset)
    mecipes = (await db.scalars(stmt)).unique().all()

    owner_names = await _load_owner_names(db, {r.user_id for r in mecipes})
    favorite_ids = await _load_favorite_ids(db, user, [r.id for r in mecipes])

    items = [
        to_summary(
            r,
            owner_display_name=owner_names.get(r.user_id, ""),
            favorite_ids=favorite_ids,
        )
        for r in mecipes
    ]
    return MecipeListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=MecipeDetail, status_code=status.HTTP_201_CREATED)
async def create_mecipe(
    payload: MecipeCreate, db: DbSession, user: CurrentUser
) -> MecipeDetail:
    tags = await upsert_tags(db, payload.tags)
    mecipe = Mecipe(
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
    db.add(mecipe)
    await db.commit()
    await db.refresh(mecipe)
    return to_detail(mecipe, owner_display_name=user.display_name)


@router.get("/{mecipe_id}", response_model=MecipeDetail)
async def get_mecipe(
    mecipe_id: UUID, db: DbSession, user: OptionalUser
) -> MecipeDetail:
    mecipe = await db.get(Mecipe, mecipe_id)
    if not mecipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mecipe not found")
    _ensure_visible(mecipe, user)
    owner_names = await _load_owner_names(db, {mecipe.user_id})
    favorite_ids = await _load_favorite_ids(db, user, [mecipe.id])
    return to_detail(
        mecipe,
        owner_display_name=owner_names.get(mecipe.user_id, ""),
        favorite_ids=favorite_ids,
    )


@router.patch("/{mecipe_id}", response_model=MecipeDetail)
async def update_mecipe(
    mecipe_id: UUID,
    payload: MecipeUpdate,
    db: DbSession,
    user: CurrentUser,
) -> MecipeDetail:
    mecipe = await db.get(Mecipe, mecipe_id)
    if not mecipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mecipe not found")
    _ensure_owner(mecipe, user)

    data = payload.model_dump(exclude_unset=True)
    for field in ("title", "description", "prep_minutes", "cook_minutes", "servings", "is_public"):
        if field in data:
            setattr(mecipe, field, data[field])

    if payload.ingredients is not None:
        mecipe.ingredients = build_ingredients(payload.ingredients)
    if payload.steps is not None:
        mecipe.steps = build_steps(payload.steps)
    if payload.tags is not None:
        mecipe.tags = await upsert_tags(db, payload.tags)

    await db.commit()
    await db.refresh(mecipe)
    return to_detail(mecipe, owner_display_name=user.display_name)


@router.delete("/{mecipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mecipe(
    mecipe_id: UUID, db: DbSession, user: CurrentUser
) -> Response:
    mecipe = await db.get(Mecipe, mecipe_id)
    if not mecipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mecipe not found")
    _ensure_owner(mecipe, user)
    await db.delete(mecipe)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
