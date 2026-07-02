"""Resolve dish photos from Wikipedia / Wikimedia Commons.

Used by image backfill and culinary audit tooling. Every returned URL is a
stable Commons thumb (default 1280px) suitable for recipe cards.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from scripts.recipe_images import image_url_is_alive

_USER_AGENT = "Mozilla/5.0 (compatible; SpiceRoute/1.0; +https://spiceroute.app)"
_THUMB_WIDTHS = (1280, 1200, 800, 440, 320)


def _sentence_case(title: str) -> str:
    """Approximate English Wikipedia article title casing."""
    small = {"a", "an", "and", "as", "at", "for", "in", "of", "on", "the", "with"}
    words = title.split()
    out: list[str] = []
    for i, word in enumerate(words):
        lower = word.lower()
        if i > 0 and lower in small:
            out.append(lower)
        else:
            out.append(word[:1].upper() + word[1:])
    return " ".join(out)


_GENERIC_WIKI_TITLES = frozenset(
    {
        "curry",
        "soup",
        "salad",
        "food",
        "noodle",
        "noodles",
        "rice",
        "stew",
        "bread",
        "cake",
        "pie",
        "sandwich",
    }
)


def _significant_tokens(title: str, slug: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", f"{title} {slug.replace('-', ' ')}".lower())
    return {w for w in words if w not in _GENERIC_WIKI_TITLES}


def _filename_matches_dish(filename: str, title: str, slug: str) -> bool:
    tokens = _significant_tokens(title, slug)
    if not tokens:
        return True
    blob = filename.lower()
    return any(token in blob for token in tokens)


def wiki_title_candidates(title: str, slug: str) -> list[str]:
    """Generate Wikipedia article title guesses, most likely first."""
    seen: set[str] = set()
    out: list[str] = []

    def add(candidate: str) -> None:
        c = candidate.strip()
        if c and c not in seen:
            seen.add(c)
            out.append(c)

    add(title)
    add(_sentence_case(title))
    add(title.lower())

    # Slug-as-phrase often matches the article (char-siu -> char siu).
    phrase = slug.replace("-", " ")
    add(phrase)
    add(_sentence_case(phrase))

    # Drop leading regional qualifiers (Hong Kong Egg Tart -> Egg Tart).
    parts = title.split()
    if len(parts) > 2:
        add(" ".join(parts[2:]))
        add(_sentence_case(" ".join(parts[2:])))

    # Common aliases before single-word fallbacks (which hit generic articles).
    aliases = {
        "tibetan-momo": ["Momo", "Momo (food)"],
        "wonton-noodle-soup": ["Wonton noodle"],
        "sri-lankan-dhal-curry": ["Dal", "Parippu", "Sri Lankan cuisine"],
        "ohn-no-khao-sw": ["Khao soi", "Ohn no khao swè"],
        "com-tam": ["Cơm tấm", "Broken rice"],
        "char-siu": ["Char siu"],
        "sichuan-mapo-tofu": ["Mapo tofu"],
        "hong-kong-egg-tart": ["Egg tart"],
        "african-chicken": ["Galinha à Africana"],
        "pork-chop-bun": ["Pork chop bun"],
        "char-siu-bao": ["Cha siu bao"],
        "red-braised-pork-belly": ["Hong shao rou"],
        "chairman-s-red-braised-pork": ["Hong shao rou"],
        "lion-s-head-meatballs": ["Lion's head meatballs"],
        "braised-lion-s-head": ["Lion's head meatballs"],
        "crossing-the-bridge-noodles": ["Crossing-the-bridge noodles"],
        "general-tso-s-chicken": ["General Tso's chicken"],
        "beggar-s-chicken": ["Beggar's chicken"],
        "vegetable-samosas": ["Samosa"],
        "mac-and-cheese": ["Macaroni and cheese"],
        "bbq-baby-back-ribs": ["Barbecue ribs"],
        "chicken-enchiladas": ["Enchilada"],
        "boeuf-bourguignon": ["Beef bourguignon"],
        "sauerkraut-with-pork": ["Sauerkraut"],
        "chicken-shawarma": ["Shawarma"],
        "iskender-kebab": ["İskender kebap"],
        "couscous-royale": ["Couscous"],
        "shiro-wat": ["Shiro (food)"],
        "kare-kare": ["Kare-kare"],
        "seekh-kebab": ["Seekh kebab"],
        "chapli-kebab": ["Chapli kebab"],
        "fish-ambul-thiyal": ["Ambul thiyal"],
        "bacalhau-br-s": ["Bacalhau à Brás"],
        "goya-champuru": ["Gōyā champurū"],
        "taco-rice": ["Taco rice"],
        "beef-rendang": ["Rendang"],
        "rendang": ["Rendang"],
    }
    for alias in aliases.get(slug, []):
        add(alias)

    if len(parts) > 1:
        last = parts[-1]
        if last.lower() not in _GENERIC_WIKI_TITLES:
            add(last)
            add(_sentence_case(last))

    return out


def _thumb_url_variants(source: str) -> list[str]:
    """Rewrite a Commons thumb URL to several allowed widths."""
    if "/thumb/" not in source:
        return [source]
    return [re.sub(r"/\d+px-", f"/{w}px-", source) for w in _THUMB_WIDTHS]


def _fetch_summary_thumb(article: str) -> str | None:
    url = (
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + urllib.parse.quote(article.replace(" ", "_"))
    )
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None
    return data.get("thumbnail", {}).get("source")


def _commons_search_thumb(query: str) -> str | None:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f'filetype:bitmap {query}',
            "gsrlimit": "5",
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "1280",
        }
    )
    url = f"https://commons.wikimedia.org/w/api.php?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return None
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        infos = page.get("imageinfo") or []
        if infos:
            thumb = infos[0].get("thumburl") or infos[0].get("url")
            if thumb:
                return thumb
    return None


def _first_live_url(candidates: list[str]) -> str | None:
    for raw in candidates:
        for url in _thumb_url_variants(raw):
            if image_url_is_alive(url):
                return url
    return None


def lookup_wikimedia_image(
    title: str,
    slug: str,
    *,
    pause_s: float = 0.15,
) -> tuple[str | None, str | None]:
    """Return `(image_url, source_label)` for a recipe title + slug."""
    for article in wiki_title_candidates(title, slug):
        if article.lower() in _GENERIC_WIKI_TITLES:
            continue
        thumb = _fetch_summary_thumb(article)
        time.sleep(pause_s)
        if not thumb:
            continue
        live = _first_live_url([thumb])
        if not live:
            continue
        fname = live.rsplit("/", 1)[-1]
        if not _filename_matches_dish(fname, title, slug):
            continue
        return live, f"wikipedia:{article}"

    # Commons file search as a last resort.
    for query in (title, slug.replace("-", " ")):
        thumb = _commons_search_thumb(query)
        time.sleep(pause_s)
        if not thumb:
            continue
        live = _first_live_url([thumb])
        if not live:
            continue
        fname = live.rsplit("/", 1)[-1]
        if _filename_matches_dish(fname, title, slug):
            return live, f"commons:{query}"

    return None, None
