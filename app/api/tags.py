from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.core.deps import DbSession
from app.models.tag import Tag
from app.schemas.mecipe import TagOut

router = APIRouter()


@router.get("", response_model=list[TagOut])
async def list_tags(
    db: DbSession,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TagOut]:
    stmt = select(Tag).order_by(Tag.name).limit(limit)
    if q:
        stmt = stmt.where(func.lower(Tag.name).like(f"%{q.lower()}%"))
    rows = (await db.scalars(stmt)).all()
    return [TagOut.model_validate(t) for t in rows]
