from typing import Protocol


class StorageBackend(Protocol):
    """Persists binary blobs (spice_route images) and returns a stable identifier.

    Implementations:
      - LocalDiskStorage (today)
      - S3Storage / R2Storage / MinIOStorage (future, single class swap)
    """

    async def save(self, data: bytes, *, filename: str) -> str:
        """Persist `data` and return an opaque path the API can store on the spice_route."""

    async def delete(self, path: str) -> None:
        """Delete a previously saved blob. Idempotent (no error if missing)."""
