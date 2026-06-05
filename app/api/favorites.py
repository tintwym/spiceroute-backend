from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, or_, select

from app.core.deps import CurrentUser, DbSession
from app.models.favorite import Favorite
from app.models.spice_route import SpiceRoute
from app.models.user import User
from app.schemas.spice_route import SpiceRouteSummary
from app.services.serialization import to_summary

router = APIRouter()


class FavoriteToggleResponse(BaseModel):
    favorited: bool


@router.post(
    "/spice_routes/{spice_route_id}/favorite",
    response_model=FavoriteToggleResponse,
    tags=["favorites"],
)
async def toggle_favorite(
    spice_route_id: UUID, db: DbSession, user: CurrentUser
) -> FavoriteToggleResponse:
    spice_route = await db.get(SpiceRoute, spice_route_id)
    if not spice_route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="spice_route not found")
    if not spice_route.is_public and spice_route.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="spice_route not found")

    existing = await db.get(Favorite, (user.id, spice_route_id))
    if existing:
        await db.delete(existing)
        await db.commit()
        return FavoriteToggleResponse(favorited=False)

    db.add(Favorite(user_id=user.id, spice_route_id=spice_route_id))
    await db.commit()
    return FavoriteToggleResponse(favorited=True)


@router.delete(
    "/spice_routes/{spice_route_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["favorites"],
)
async def remove_favorite(spice_route_id: UUID, db: DbSession, user: CurrentUser):
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user.id, Favorite.spice_route_id == spice_route_id
        )
    )
    await db.commit()


@router.get(
    "/me/favorites",
    response_model=list[SpiceRouteSummary],
    tags=["favorites"],
)
async def list_my_favorites(
    db: DbSession, user: CurrentUser
) -> list[SpiceRouteSummary]:
    fav_subq = select(Favorite.spice_route_id).where(Favorite.user_id == user.id)
    # Apply the same visibility rule as the rest of the API: a spice_route is
    # visible to a user if it's public OR they own it. If someone made a
    # public spice_route private after you favorited it, you lose access here
    # too. Keeps /me/favorites and /spice_routes?favorites_only=true in sync.
    spice_routes = (
        await db.scalars(
            select(SpiceRoute)
            .where(
                SpiceRoute.id.in_(fav_subq),
                or_(SpiceRoute.is_public.is_(True), SpiceRoute.user_id == user.id),
            )
            .order_by(SpiceRoute.created_at.desc())
        )
    ).unique().all()
    user_ids = {r.user_id for r in spice_routes}
    owners = {
        row.id: row.display_name
        for row in await db.execute(
            select(User.id, User.display_name).where(User.id.in_(user_ids))
        )
    }
    favorite_ids = {r.id for r in spice_routes}
    return [
        to_summary(
            r,
            owner_display_name=owners.get(r.user_id, ""),
            favorite_ids=favorite_ids,
        )
        for r in spice_routes
    ]
