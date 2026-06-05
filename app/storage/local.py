from pathlib import Path
from uuid import uuid4

import aiofiles


class LocalDiskStorage:
    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, *, filename: str) -> str:
        ext = Path(filename).suffix.lower() or ".bin"
        out_name = f"{uuid4().hex}{ext}"
        out_path = self.base / out_name
        async with aiofiles.open(out_path, "wb") as f:
            await f.write(data)
        return out_name

    async def delete(self, path: str) -> None:
        # Defense in depth: reject anything that could escape `self.base`.
        # Today `save()` always returns "<hex>.<ext>" so this is unreachable,
        # but a tampered DB row could otherwise let us delete arbitrary files.
        if "/" in path or "\\" in path or path.startswith(".") or ".." in path:
            return
        target = self.base / path
        try:
            target.unlink()
        except FileNotFoundError:
            pass
