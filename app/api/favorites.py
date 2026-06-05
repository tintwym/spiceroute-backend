from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, or_, select

from app.core.deps import CurrentUser, DbSession
from app.models.favorite import Favorite
from app.models.mecipe import Mecipe
from app.models.user import User
from app.schemas.mecipe import MecipeSummary
from app.services.serialization import to_summary

router = APIRouter()


class FavoriteToggleResponse(BaseModel):
    favorited: bool


@router.post(
    "/mecipes/{mecipe_id}/favorite",
    response_model=FavoriteToggleResponse,
    tags=["favorites"],
)
async def toggle_favorite(
    mecipe_id: UUID, db: DbSession, user: CurrentUser
) -> FavoriteToggleResponse:
    mecipe = await db.get(Mecipe, mecipe_id)
    if not mecipe:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mecipe not found")
    if not mecipe.is_public and mecipe.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mecipe not found")

    existing = await db.get(Favorite, (user.id, mecipe_id))
    if existing:
        await db.delete(existing)
        await db.commit()
        return FavoriteToggleResponse(favorited=False)

    db.add(Favorite(user_id=user.id, mecipe_id=mecipe_id))
    await db.commit()
    return FavoriteToggleResponse(favorited=True)


@router.delete(
    "/mecipes/{mecipe_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["favorites"],
)
async def remove_favorite(mecipe_id: UUID, db: DbSession, user: CurrentUser):
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user.id, Favorite.mecipe_id == mecipe_id
        )
    )
    await db.commit()


@router.get(
    "/me/favorites",
    response_model=list[MecipeSummary],
    tags=["favorites"],
)
async def list_my_favorites(
    db: DbSession, user: CurrentUser
) -> list[MecipeSummary]:
    fav_subq = select(Favorite.mecipe_id).where(Favorite.user_id == user.id)
    # Apply the same visibility rule as the rest of the API: a mecipe is
    # visible to a user if it's public OR they own it. If someone made a
    # public mecipe private after you favorited it, you lose access here too.
    # This keeps /me/favorites and /mecipes?favorites_only=true in sync.
    mecipes = (
        await db.scalars(
            select(Mecipe)
            .where(
                Mecipe.id.in_(fav_subq),
                or_(Mecipe.is_public.is_(True), Mecipe.user_id == user.id),
            )
            .order_by(Mecipe.created_at.desc())
        )
    ).unique().all()
    user_ids = {r.user_id for r in mecipes}
    owners = {
        row.id: row.display_name
        for row in await db.execute(
            select(User.id, User.display_name).where(User.id.in_(user_ids))
        )
    }
    favorite_ids = {r.id for r in mecipes}
    return [
        to_summary(
            r,
            owner_display_name=owners.get(r.user_id, ""),
            favorite_ids=favorite_ids,
        )
        for r in mecipes
    ]
