from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.spice_route import SpiceRoute
from app.services.serialization import image_url
from app.storage import get_storage

router = APIRouter()
settings = get_settings()

ALLOWED_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class ImageUploadResponse(BaseModel):
    image_url: str


@router.post("/{spice_route_id}/image", response_model=ImageUploadResponse)
async def upload_spice_route_image(
    spice_route_id: UUID,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> ImageUploadResponse:
    spice_route = await db.get(SpiceRoute, spice_route_id)
    if not spice_route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="spice_route not found")
    if spice_route.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not the spice_route owner")

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported image type: {content_type or 'unknown'}",
        )

    data = await file.read()
    if len(data) > settings.max_image_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"image exceeds {settings.max_image_bytes} bytes",
        )
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="empty file"
        )

    storage = get_storage()
    # IMPORTANT: derive the extension from the validated MIME type, NOT the
    # user-supplied filename. Otherwise a user uploading "evil.png.exe" with
    # content-type image/png would get the file saved as ".exe" and served
    # with content-type application/octet-stream (browser would download it).
    canonical_filename = f"hero{ALLOWED_MIME[content_type]}"
    saved_path = await storage.save(data, filename=canonical_filename)

    # Save new path to DB BEFORE deleting the old file. If the commit fails
    # we'd rather orphan a (just-saved) blob than be left with a DB row
    # pointing to a deleted file.
    old_path = spice_route.image_path
    spice_route.image_path = saved_path
    try:
        await db.commit()
    except Exception:
        await storage.delete(saved_path)
        raise

    if old_path:
        await storage.delete(old_path)

    return ImageUploadResponse(image_url=image_url(saved_path) or "")
