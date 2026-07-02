"""Stable, CDN-hosted food photos for recipe cards.

LoremFlickr search URLs used to resolve at seed time but now frequently
return HTTP 500. Cards then hit the emoji placeholder even though
`image_path` is non-null in Postgres.

We pin each recipe to a deterministic Unsplash photo (imgix-backed, works
from web/mobile) or a hand-verified Wikimedia Commons thumb when available.

Every Unsplash ID below was HEAD-verified before landing in this tuple.
Do not add IDs without running `tests/test_recipe_images.py`.
"""
from __future__ import annotations

import time
import urllib.error
import urllib.request
import zlib

_USER_AGENT = "Mozilla/5.0 (compatible; SpiceRoute/1.0; +https://spiceroute.app)"

# Hand-picked Unsplash food photos (license: Unsplash). All verified HTTP 200.
_UNSPLASH_FOOD_PHOTOS: tuple[str, ...] = (
    "photo-1546069901-ba9599a7e63c",
    "photo-1540189549336-e6e99c3679fe",
    "photo-1546793665-c74683f339c1",
    "photo-1547592180-85f173990554",
    "photo-1550547660-d9450f859349",
    "photo-1551218808-94e220e084d2",
    "photo-1553621042-f6e147245754",
    "photo-1555939594-58d7cb561ad1",
    "photo-1565299624946-b28f40a0ae38",
    "photo-1565958011703-44f9829ba187",
    "photo-1567620905732-2d1ec7ab7445",
    "photo-1586190848861-99aa4a171e90",
    "photo-1589302168068-964664d93dc0",
    "photo-1504674900247-0877df9cc836",
    "photo-1512058564366-18510be2db19",
    "photo-1512621776951-a57141f2eefd",
    "photo-1621996346565-e3dbc646d9a9",
    "photo-1626700051175-6818013e1d4f",
    "photo-1482049016688-2d3e1b311543",
    "photo-1525351484163-7529414344d8",
    "photo-1530554764233-e79e16c91d08",
    "photo-1534422298391-e4f8c172dddb",
    "photo-1540420773420-3366772f4999",
    "photo-1551782450-a2132b4ba21d",
    "photo-1563379926898-05f4575a45d8",
    "photo-1565299507177-b0ac66763828",
    "photo-1571091718767-18b5b1457add",
    "photo-1578662996442-48f60103fc96",
    "photo-1585032226651-759b368d7246",
    "photo-1585515320310-259814833e62",
    "photo-1596797038530-2c107229654b",
)


def stable_food_image_url(slug: str, *, width: int = 1200, height: int = 800) -> str:
    """Return a stable Unsplash CDN URL for a recipe slug or title."""
    key = (slug or "food").strip().lower()
    digest = zlib.crc32(key.encode("utf-8"))
    idx = digest % len(_UNSPLASH_FOOD_PHOTOS)
    photo_id = _UNSPLASH_FOOD_PHOTOS[idx]
    focal = ((digest >> 8) % 80) + 10
    return (
        f"https://images.unsplash.com/{photo_id}"
        f"?w={width}&h={height}&fit=crop&crop=entropy&fp-z={focal / 100:.2f}"
        f"&auto=format&q=80"
    )


def is_broken_image_url(url: str | None) -> bool:
    """True when the stored URL should be replaced."""
    if not url:
        return True
    lowered = url.lower()
    return (
        "loremflickr.com" in lowered
        or "picsum.photos" in lowered
        or "defaultimage" in lowered
    )


def image_url_is_alive(url: str, *, timeout: float = 15.0, retries: int = 2) -> bool:
    """Return True when the URL responds HTTP 200.

    Wikimedia blocks bare HEAD requests and rate-limits bursts — use GET
    with a descriptive User-Agent and retry on 429.
    """
    if is_broken_image_url(url):
        return False
    headers = {"User-Agent": _USER_AGENT}
    method = "GET" if "wikimedia.org" in url else "HEAD"
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return True
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return False
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
    return False
