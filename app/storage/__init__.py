from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalDiskStorage


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    return LocalDiskStorage(settings.image_storage_dir)
