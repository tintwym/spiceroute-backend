from fastapi import APIRouter
from sqlalchemy import text

from app.core.deps import DbSession

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: DbSession) -> dict:
    result = await db.execute(text("SELECT 1"))
    db_ok = result.scalar() == 1
    return {"status": "ok", "database": "ok" if db_ok else "down"}
