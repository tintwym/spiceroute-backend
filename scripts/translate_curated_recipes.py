"""Bulk-translate curated recipe titles + descriptions via Gemini.

ORTHOGONAL TO THE RUNTIME AI BACKEND. The app's user-facing AI Creator
and AI Companion run against whatever OpenAI-compatible provider is
configured at LLM_BASE_URL / LLM_API_KEY (see `app/services/ai/llm.py`)
— Groq by default in production. This script stays on Gemini purely
because Gemini 2.5 Flash gives noticeably better multilingual
translation quality than the smaller models we use for the live API,
and the script only runs when we add new curated rows.

`google-genai` is NOT in `pyproject.toml`'s runtime deps. Install it
on-demand in your local venv when you actually need to retranslate:

    uv pip install google-genai

Reads CURATED from `scripts/curated_data.py`, calls Gemini to translate
each recipe's title and description into the 4 non-English locales
SpiceRoute supports (zh, ja, ko, vi), and writes the resulting
`"translations": {...}` blocks back into `curated_data.py` in place —
preserving every line of the original file except the inserted blocks.

WHY THIS EXISTS
---------------
The Explore grid backs each card with a recipe row whose `title` and
`description` are static columns. Without per-locale overrides a Korean
user viewing the seeded Quiche Lorraine card sees:

    Eyebrow:     프랑스                              (UI chrome, properly translated)
    Title:       Quiche Lorraine                    ← English leak
    Description: Buttery shortcrust filled…         ← English leak
    Time/yield:  1시간 15분                         (UI chrome, properly translated)

The runtime swap happens server-side via `?translate_to=<locale>` on
the recipes endpoints (see `app/api/spice_routes.py::_resolve_translation`).
This script fills the `spice_routes.translations` JSONB column with the
content the endpoint will hand back to non-English clients.

DESIGN NOTES
------------
1. **In-place source surgery, not a sidecar JSON file.** Curated recipes
   live in version control and benefit from being reviewable inline.
   Inserting via Python AST + line ranges guarantees the rest of the
   file (the FLICKR keyword table, the WIKIMEDIA URL map, every other
   recipe's metadata) is preserved verbatim.

2. **Idempotent by default.** Recipes that already have a `translations`
   key are SKIPPED unless `--force` is passed. So you can:
     - Re-run after adding new recipes to translate only the newcomers.
     - Re-run after a partial Gemini outage without re-translating what
       already succeeded.
     - Hand-polish a few specs (e.g. the 3 French ones) and never have
       this tool overwrite them.

3. **One Gemini call per recipe.** The 4 locales come back together in
   a single structured-JSON response, so 33 recipes × 1 call ≈ 33
   calls. With Flash, ~$0.01 total. We could batch, but a single
   recipe per call gives us clean per-row error isolation and easy
   retry semantics.

4. **Title fallback is built in.** The endpoint's
   `_resolve_translation` falls back to the source title (English) when
   a per-locale `title` entry is missing or empty — so locales with no
   conventional transliteration of a dish name (rare, but real) can
   safely return only a translated description and the card still
   reads coherently.

USAGE
-----
    # Translate every recipe that doesn't already have translations.
    GEMINI_API_KEY=sk-... python scripts/translate_curated_recipes.py

    # Translate only the first 3 recipes (smoke test).
    python scripts/translate_curated_recipes.py --limit 3

    # Re-translate everything from scratch (overwrites existing entries
    # in curated_data.py — be CAREFUL: this clobbers hand-polished
    # translations like the French set).
    python scripts/translate_curated_recipes.py --force

    # See what would change without writing anything.
    python scripts/translate_curated_recipes.py --dry-run

After the script writes, **review the diff** before committing:
    git diff scripts/curated_data.py | less

Then run the seeder against your DB to backfill the live rows:
    python scripts/seed_curated_recipes.py --quick
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

# Add the backend root to sys.path so we can `import scripts.curated_data`
# even when this script is invoked from the project root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.curated_data import CURATED  # noqa: E402
from scripts.translation_utils import (  # noqa: E402
    invalid_locale_codes,
    is_garbage_translation_text,
    is_stub_locale_bundle,
    merge_translation_bundle,
)

TARGET_LOCALES = ("zh", "ja", "ko", "vi")

LOCALE_NAMES: dict[str, str] = {
    "zh": "Simplified Chinese (Mandarin)",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
}

SCRIPTS_DIR = ROOT / "scripts"


def _load_local_dotenv() -> None:
    """Load repo-root `.env` into os.environ (keys already set win).

    `uv run python scripts/...` does not auto-load `.env` like pydantic
    Settings does for the API. Without this, GEMINI_API_KEY in `.env`
    is invisible and the script falls through to Groq/LLM_*.
    """
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        os.environ.setdefault(key, value.strip())


# Every Python module that owns a curated recipe list. Expansion batches
# live outside curated_data.py but are merged into CURATED at import time;
# this table is how we write translations back to the right file.
SOURCE_TARGETS: list[tuple[Path, str]] = [
    (SCRIPTS_DIR / "curated_data.py", "CURATED"),
    (SCRIPTS_DIR / "cuisine_expansion_v5_east_asia.py", "EAST_ASIA_EXPANSION_RECIPES"),
    (SCRIPTS_DIR / "cuisine_expansion_v6_original.py", "ORIGINAL_EXPANSION_RECIPES"),
    (SCRIPTS_DIR / "cuisine_expansion_v7_myanmar.py", "MYANMAR_EXPANSION_RECIPES"),
]

CURATED_DATA_FILE = SCRIPTS_DIR / "curated_data.py"


@dataclass(frozen=True)
class RecipeTarget:
    source_file: Path
    list_name: str
    title: str
    node: ast.Dict


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------


def _build_prompt(title: str, description: str, cuisine: str) -> str:
    locale_lines = "\n".join(
        f"  - {code}: {name}" for code, name in LOCALE_NAMES.items()
    )
    return f"""You are localizing a recipe card for SpiceRoute, a global
recipes app. Translate the title and description into the following five
locales:

{locale_lines}

Source recipe:
  Cuisine:     {cuisine}
  Title:       {title}
  Description: {description}

Translation guidelines:

* TITLES — Never copy the English title verbatim into zh/ja/ko/vi.
  Internationally-known dish names must be written in the target script
  the way native speakers list them on menus (とんかつ, 돈가스, 叉烧,
  Bánh mì kẹp thịt, etc.). Descriptive English titles (e.g. "Braised
  Lion's Head") should become natural dish names in that language.
* DESCRIPTIONS — Translate faithfully and concisely. Never copy the
  English description verbatim. Keep the warm, inviting tone of food
  writing. Aim for similar length to the source.
* Use the target-language script throughout (no romanization mixed in
  unless the source had it).
* Do NOT add commentary, footnotes, or attribution.

Return ONLY a JSON object in exactly this shape (no markdown fences,
no surrounding prose, no trailing commas):

{{
  "zh": {{"title": "...", "description": "..."}},
  "ja": {{"title": "...", "description": "..."}},
  "ko": {{"title": "...", "description": "..."}},
  "vi": {{"title": "...", "description": "..."}}
}}
"""


def _extract_retry_delay_seconds(exc: Exception) -> float | None:
    """Pull the `retryDelay` value out of a Gemini 429 error payload.

    The API returns it inside a structured QuotaFailure block, e.g.
    `{'@type': 'type.googleapis.com/google.rpc.RetryInfo',
       'retryDelay': '23s'}`. Honouring this is the difference between
    waiting ~25 s once vs. burning the rest of the run on a chain of
    immediate retries that each get throttled again.

    The google-genai SDK stuffs the raw error JSON into `exc.args[0]`
    or `str(exc)` depending on the SDK version, so we string-grep
    rather than poke at the structured details (which aren't part of
    the SDK's public surface).
    """
    text = str(exc)
    # Match patterns like "'retryDelay': '23s'" or "'retryDelay': '24.99s'"
    import re

    m = re.search(r"['\"]retryDelay['\"]\s*:\s*['\"]?([\d.]+)s['\"]?", text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _call_gemini(
    title: str,
    description: str,
    cuisine: str,
    *,
    max_retries: int = 5,
) -> dict[str, Any]:
    from google import genai  # type: ignore[import-untyped]
    from google.genai import types  # type: ignore[import-untyped]

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "GEMINI_API_KEY is required. Export it or pass via env, e.g.\n"
            "  GEMINI_API_KEY=sk-... python scripts/translate_curated_recipes.py"
        )

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.35,
    )
    # Retry loop. Two distinct retryable failure modes:
    #   429 RESOURCE_EXHAUSTED — free tier quota (5 RPM) is exhausted.
    #     The API tells us *exactly* how long to wait via `retryDelay`
    #     in the structured error; we honour it (+ a small jitter).
    #   503 UNAVAILABLE        — "high demand" transient capacity error.
    #     Pure server-side blip; an exponential backoff with a few
    #     attempts almost always recovers.
    # Anything else (bad request, auth failure, etc.) bubbles up
    # immediately — no point retrying.
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=_build_prompt(title, description, cuisine),
                config=config,
            )
            break
        except Exception as exc:
            text = str(exc)
            last_exc = exc
            if "RESOURCE_EXHAUSTED" in text or "429" in text:
                wait = _extract_retry_delay_seconds(exc) or 30.0
                wait += 2.0  # small buffer so we don't hit the boundary
                print(
                    f"  · 429 quota — sleeping {wait:.0f}s before retry "
                    f"({attempt + 1}/{max_retries})",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait)
                continue
            if "UNAVAILABLE" in text or "503" in text:
                wait = min(2 ** attempt * 5, 60)  # 5, 10, 20, 40, 60
                print(
                    f"  · 503 transient — sleeping {wait}s before retry "
                    f"({attempt + 1}/{max_retries})",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise
    else:
        # Loop exhausted without success.
        raise RuntimeError(
            f"giving up on {title!r} after {max_retries} retries: {last_exc}"
        ) from last_exc
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError(f"empty response from gemini for {title!r}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"gemini returned non-JSON for {title!r}:\n{text}"
        ) from exc
    return data


def _clean_translation_payload(
    data: Any,
    *,
    source_title: str,
    source_description: str | None,
) -> dict[str, dict[str, str]]:
    if not isinstance(data, dict):
        return {}
    cleaned: dict[str, dict[str, str]] = {}
    for locale in TARGET_LOCALES:
        entry = data.get(locale)
        if not isinstance(entry, dict):
            continue
        out: dict[str, str] = {}
        t = entry.get("title")
        if isinstance(t, str) and t.strip():
            out["title"] = t.strip()
        d = entry.get("description")
        if isinstance(d, str) and d.strip():
            out["description"] = d.strip()
        if not out:
            continue
        if is_stub_locale_bundle(
            out, source_title=source_title, source_description=source_description
        ):
            continue
        if is_garbage_translation_text(out.get("title"), field="title") or is_garbage_translation_text(
            out.get("description"), field="description"
        ):
            continue
        cleaned[locale] = out
    return cleaned


def _call_openai_compatible(
    title: str,
    description: str,
    cuisine: str,
    *,
    max_retries: int = 5,
    allow_partial: bool = False,
) -> dict[str, dict[str, str]]:
    """Single-call translation via the app's OpenAI-compatible LLM."""
    from app.core.config import get_settings

    settings = get_settings()
    base = (settings.llm_base_url or os.environ.get("LLM_BASE_URL", "")).strip().rstrip("/")
    api_key = (settings.llm_api_key or os.environ.get("LLM_API_KEY", "")).strip()
    model = (
        os.environ.get("TRANSLATE_LLM_MODEL")
        or settings.llm_model
        or os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
    ).strip()
    # The live API default (8b-instant) is too small for reliable
    # quadrilingual card copy — garbage strings slipped through CI.
    if model == "llama-3.1-8b-instant":
        model = "llama-3.3-70b-versatile"
    if not base or not api_key:
        raise SystemExit(
            "LLM_BASE_URL + LLM_API_KEY are required when GEMINI_API_KEY is unset.\n"
            "  export them in .env or pass via env."
        )

    payload = {
        "model": model,
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You localize recipe cards. Return ONLY valid JSON with no "
                    "markdown fences."
                ),
            },
            {"role": "user", "content": _build_prompt(title, description, cuisine)},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    use_json_mode = True
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        req = dict(payload)
        if use_json_mode:
            req["response_format"] = {"type": "json_object"}
        else:
            req.pop("response_format", None)
        try:
            with httpx.Client(timeout=120.0) as http:
                resp = http.post(f"{base}/chat/completions", json=req, headers=headers)
                resp.raise_for_status()
                body = resp.json()
            text = (
                body.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not text:
                raise RuntimeError(f"empty LLM response for {title!r}")
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].strip()
            data = json.loads(text)
            cleaned = _clean_translation_payload(
                data,
                source_title=title,
                source_description=description,
            )
            bad = invalid_locale_codes(
                cleaned,
                source_title=title,
                source_description=description,
            )
            if cleaned and (not bad or allow_partial):
                if bad and allow_partial:
                    for loc in bad:
                        cleaned.pop(loc, None)
                if cleaned:
                    return cleaned
            last_exc = RuntimeError(
                f"LLM returned incomplete/invalid locales for {title!r}: "
                f"{bad or ['empty']}"
            )
            if attempt + 1 < max_retries:
                time.sleep(min(2 ** attempt * 2, 15))
                continue
            raise last_exc
        except httpx.HTTPStatusError as exc:
            last_exc = exc
            if exc.response.status_code == 400 and use_json_mode:
                use_json_mode = False
                continue
            if exc.response.status_code in {429, 503}:
                wait = min(2 ** attempt * 5, 60)
                print(
                    f"  · {exc.response.status_code} — sleeping {wait}s "
                    f"({attempt + 1}/{max_retries})",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise
        except json.JSONDecodeError as exc:
            last_exc = exc
            use_json_mode = False
            if attempt + 1 < max_retries:
                time.sleep(min(2 ** attempt * 2, 10))
                continue
            raise
        except Exception as exc:
            last_exc = exc
            if attempt + 1 < max_retries:
                time.sleep(min(2 ** attempt * 2, 20))
                continue
            raise
    raise RuntimeError(
        f"giving up on {title!r} after {max_retries} retries: {last_exc}"
    ) from last_exc


def _call_provider(
    title: str,
    description: str,
    cuisine: str,
    *,
    max_retries: int = 5,
    allow_partial: bool = False,
) -> dict[str, dict[str, str]]:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            if os.environ.get("GEMINI_API_KEY", "").strip():
                raw = _call_gemini(title, description, cuisine)
            else:
                return _call_openai_compatible(
                    title,
                    description,
                    cuisine,
                    max_retries=max_retries,
                    allow_partial=allow_partial,
                )
            cleaned = _clean_translation_payload(
                raw,
                source_title=title,
                source_description=description,
            )
            bad = invalid_locale_codes(
                cleaned,
                source_title=title,
                source_description=description,
            )
            if cleaned and (not bad or allow_partial):
                if bad and allow_partial:
                    for loc in bad:
                        cleaned.pop(loc, None)
                if cleaned:
                    return cleaned
            last_exc = RuntimeError(
                f"incomplete/invalid locales for {title!r}: {bad or ['empty']}"
            )
            if attempt + 1 < max_retries:
                wait = min(2 ** attempt * 2, 15)
                print(
                    f"  · retrying after bad locales ({attempt + 1}/{max_retries})",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise last_exc
        except Exception as exc:
            last_exc = exc
            if attempt + 1 < max_retries:
                time.sleep(min(2 ** attempt * 2, 15))
                continue
            raise
    raise RuntimeError(
        f"giving up on {title!r} after {max_retries} retries: {last_exc}"
    ) from last_exc


# ---------------------------------------------------------------------------
# AST-driven source surgery
# ---------------------------------------------------------------------------


def _find_recipe_dicts(
    source: str,
    *,
    list_name: str = "CURATED",
) -> list[tuple[str, ast.Dict]]:
    """Return `(title, ast.Dict)` for every recipe in `list_name`, in source
    order.

    Walks the module AST to locate the curated list assignment and yields
    each list element. We need the AST node (not just the title string) so
    the caller can read `node.end_lineno` to know where to splice the
    translations block.
    """
    tree = ast.parse(source)
    curated_list: ast.List | None = None
    for stmt in tree.body:
        if isinstance(stmt, ast.AnnAssign):
            if (
                isinstance(stmt.target, ast.Name)
                and stmt.target.id == list_name
                and isinstance(stmt.value, ast.List)
            ):
                curated_list = stmt.value
                break
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == list_name:
                    if isinstance(stmt.value, ast.List):
                        curated_list = stmt.value
                    break
            if curated_list is not None:
                break
    if curated_list is None:
        raise RuntimeError(
            f"Couldn't locate `{list_name} = [...]` — did the schema change?"
        )

    results: list[tuple[str, ast.Dict]] = []
    for elt in curated_list.elts:
        if not isinstance(elt, ast.Dict):
            continue
        title: str | None = None
        for k, v in zip(elt.keys, elt.values, strict=False):
            if (
                isinstance(k, ast.Constant)
                and k.value == "title"
                and isinstance(v, ast.Constant)
                and isinstance(v.value, str)
            ):
                title = v.value
                break
        if title:
            results.append((title, elt))
    return results


def _collect_translation_targets(
    *,
    force: bool,
    repair: bool,
    titles: list[str] | None,
) -> list[RecipeTarget]:
    spec_by_title = {spec["title"]: spec for spec in CURATED}
    targets: list[RecipeTarget] = []
    for source_file, list_name in SOURCE_TARGETS:
        if not source_file.is_file():
            continue
        source = source_file.read_text(encoding="utf-8")
        for title, node in _find_recipe_dicts(source, list_name=list_name):
            if titles and title not in titles:
                continue
            spec = spec_by_title.get(title)
            if repair:
                if spec is None:
                    continue
                bad = invalid_locale_codes(
                    spec.get("translations"),
                    source_title=spec["title"],
                    source_description=spec.get("description"),
                )
                if not bad:
                    continue
            elif _has_translations(node) and not force:
                continue
            targets.append(
                RecipeTarget(
                    source_file=source_file,
                    list_name=list_name,
                    title=title,
                    node=node,
                )
            )
    return targets


def _has_translations(node: ast.Dict) -> bool:
    return _translations_line_range(node) is not None


def _translations_line_range(node: ast.Dict) -> tuple[int, int] | None:
    """Return `(start_line, end_line)` 1-indexed inclusive of the
    existing `"translations": {...},` entry within `node`, or None
    if the recipe doesn't have one yet.

    Used both as a presence check (for the default
    skip-if-already-translated guard) and as the splice target when
    `--force` is set — replacing the existing entry in place avoids
    introducing duplicate dict keys, which Python silently allows but
    is a source-readability foot-gun.
    """
    for k, v in zip(node.keys, node.values, strict=False):
        if (
            isinstance(k, ast.Constant)
            and k.value == "translations"
            and k.lineno is not None
        ):
            end = getattr(v, "end_lineno", None)
            if end is not None:
                return (k.lineno, end)
    return None


def _format_translations_block(translations: dict[str, dict[str, str]]) -> str:
    """Render the translations dict as a Python source fragment at the
    correct indent (8 spaces — recipe-dict key level).

    We hand-write the formatting instead of using `pprint` because:
    1. pprint's indentation rules don't match ruff's, so the file would
       lint-fail on commit.
    2. We need stable, line-by-line output so `git diff` highlights only
       the actual content changes (not whitespace churn) when this
       script re-runs.

    Output is a single string ending with `\\n` so callers can prepend
    it directly into the source line list.
    """
    # Indent layout — mirrors the hand-written French entries:
    #
    #         "translations": {        ← 8 spaces (recipe-dict key level)
    #             "zh": {              ← 12 spaces (locale key)
    #                 "title": "...",  ← 16 spaces (inner key)
    #                 "description": "...",
    #             },                   ← 12 (close locale)
    #         },                       ← 8  (close translations)
    lines: list[str] = ['        "translations": {']
    for locale in TARGET_LOCALES:
        bundle = translations.get(locale)
        if not bundle:
            continue
        lines.append(f'            "{locale}": {{')
        # Stable key order: title before description, matching the
        # hand-written French entries already in the file.
        for key in ("title", "description"):
            value = bundle.get(key)
            if value is None:
                continue
            # `repr` would escape non-ASCII into `\uXXXX` codepoints —
            # we want the CJK / Burmese characters to live in the
            # source verbatim so reviewers can read them. `json.dumps`
            # with `ensure_ascii=False` gives us exactly that, plus
            # correct escaping of any embedded quotes / backslashes.
            literal = json.dumps(value, ensure_ascii=False)
            lines.append(f'                "{key}": {literal},')
        # Close the per-locale block. Trailing comma matches the
        # rest of curated_data.py's style.
        lines.append("            },")
    lines.append("        },")
    return "\n".join(lines) + "\n"


def _splice_translations(
    source: str,
    additions: list[tuple[ast.Dict, dict[str, dict[str, str]]]],
) -> str:
    """Splice each `translations` block into the source.

    Two cases per recipe:

    * **Insert** — recipe has no existing `translations` key. The new
      block goes immediately before the closing `}` of the recipe dict
      (between the last existing key and the dict terminator).
    * **Replace** — recipe already has a `translations` entry and the
      caller passed `--force`. We delete the existing entry's line
      range and write the new block in its place. Avoids creating a
      duplicate `"translations"` key (which Python silently accepts
      but is confusing in source).

    Applies in REVERSE line order so earlier splices don't shift the
    line numbers of later ones. Walking forward and adjusting line
    numbers as we go is fragile when one of the recipes happens to
    span a different number of lines than we expect.
    """
    lines = source.splitlines(keepends=True)
    # Sort additions descending by end_lineno so a higher-index splice
    # never invalidates a lower-index splice's target position.
    additions.sort(key=lambda pair: pair[0].end_lineno or 0, reverse=True)
    for node, translations in additions:
        if node.end_lineno is None:
            continue
        block = _format_translations_block(translations)
        existing = _translations_line_range(node)
        if existing is not None:
            start, end = existing
            # Replace lines [start..end] (1-indexed, inclusive). Slice
            # is [start-1:end] which is 0-indexed exclusive end. The
            # block ends with `\n` so the surrounding lines stay
            # vertically aligned.
            lines[start - 1 : end] = [block]
        else:
            insert_at = node.end_lineno - 1
            lines.insert(insert_at, block)
    return "".join(lines)


# ---------------------------------------------------------------------------
# CLI driver
# ---------------------------------------------------------------------------


def _persist_one(
    target: RecipeTarget,
    translations: dict[str, dict[str, str]],
) -> None:
    """Re-parse the source module, find the recipe dict, splice translations."""
    src = target.source_file.read_text(encoding="utf-8")
    fresh_nodes = _find_recipe_dicts(src, list_name=target.list_name)
    match: ast.Dict | None = None
    for fresh_title, node in fresh_nodes:
        if fresh_title == target.title:
            match = node
            break
    if match is None:
        print(
            f"  ! Warning: couldn't relocate {target.title!r} in "
            f"{target.source_file.name}; skipping persist",
            file=sys.stderr,
        )
        return
    new_src = _splice_translations(src, [(match, translations)])
    target.source_file.write_text(new_src, encoding="utf-8")


def main() -> int:
    _load_local_dotenv()
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing curated_data.py.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-translate recipes that already have a `translations` key. "
            "WARNING: clobbers hand-polished entries (the French recipes "
            "currently in the file)."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Translate at most N recipes this run (top of the list "
            "wins). Useful for smoke-testing the Gemini integration "
            "without spending the full ~$0.01 / 33 calls."
        ),
    )
    parser.add_argument(
        "--titles",
        nargs="+",
        default=None,
        help=(
            "Restrict to specific recipes by title (case-sensitive "
            "exact match). Use to re-translate a single dish you're "
            "unhappy with."
        ),
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help=(
            "Re-translate only recipes whose zh/ja/ko/vi bundles are "
            "missing, English stubs, or corrupt LLM garbage. Safer than "
            "--force because hand-polished recipes are left alone."
        ),
    )
    parser.add_argument(
        "--rpm",
        type=float,
        default=4.0,
        help=(
            "Throttle to at most N requests per minute. Default 4.0 "
            "stays comfortably under the gemini-2.5-flash free-tier "
            "limit of 5 RPM. Bump to e.g. 60 for paid tier (1000 "
            "RPM) so the run finishes in seconds instead of minutes. "
            "Set to 0 to disable client-side throttling entirely and "
            "lean only on the server's 429 retry-after responses."
        ),
    )
    args = parser.parse_args()

    to_translate = _collect_translation_targets(
        force=args.force,
        repair=args.repair,
        titles=args.titles,
    )

    if args.limit is not None:
        to_translate = to_translate[: args.limit]

    if not to_translate:
        print(
            "Nothing to translate. "
            "Pass --force to re-translate recipes that already have entries, "
            "or --repair to fix corrupt/missing locale bundles only."
        )
        return 0

    use_force_merge = args.force or args.repair

    provider = (
        "gemini"
        if os.environ.get("GEMINI_API_KEY", "").strip()
        else "openai-compatible (LLM_BASE_URL)"
    )
    print(f"Will translate {len(to_translate)} recipe(s) via {provider}:")
    for item in to_translate:
        print(f"  - {item.title} ({item.source_file.name})")
    print()

    spec_by_title = {spec["title"]: spec for spec in CURATED}

    min_interval = 60.0 / args.rpm if args.rpm > 0 else 0.0
    last_call_at: float | None = None

    additions: list[tuple[RecipeTarget, dict[str, dict[str, str]]]] = []
    for i, item in enumerate(to_translate, start=1):
        spec = spec_by_title.get(item.title)
        if spec is None:
            print(f"  ! Skipped {item.title!r}: not in CURATED import", file=sys.stderr)
            continue

        if last_call_at is not None and min_interval > 0:
            elapsed = time.monotonic() - last_call_at
            if elapsed < min_interval:
                wait = min_interval - elapsed
                if wait > 1.0:
                    print(
                        f"  · pacing — sleeping {wait:.1f}s "
                        f"(--rpm={args.rpm:g})",
                        flush=True,
                    )
                time.sleep(wait)

        print(
            f"[{i}/{len(to_translate)}] {item.title} ({spec['cuisine']})…",
            flush=True,
        )
        last_call_at = time.monotonic()
        try:
            translations = _call_provider(
                title=item.title,
                description=spec["description"],
                cuisine=spec["cuisine"],
                allow_partial=args.repair,
            )
        except Exception as exc:
            print(f"  ! Skipped: {exc}", file=sys.stderr)
            continue

        # --repair/--force: shallow-merge fresh title/description into any
        # existing per-locale ingredients/steps. Default: only fill stubs.
        existing_tr = spec.get("translations")
        if use_force_merge and isinstance(existing_tr, dict):
            merged_tr = dict(existing_tr)
            for loc, bundle in translations.items():
                prev = dict(merged_tr.get(loc) or {})
                prev.update(bundle)
                merged_tr[loc] = prev
            # Drop title/description keys that are still garbage after merge.
            for loc, bundle in list(merged_tr.items()):
                if not isinstance(bundle, dict):
                    continue
                cleaned = dict(bundle)
                for fld in ("title", "description"):
                    val = cleaned.get(fld)
                    if isinstance(val, str) and is_garbage_translation_text(
                        val, field=fld
                    ):
                        cleaned.pop(fld, None)
                if cleaned:
                    merged_tr[loc] = cleaned
                else:
                    merged_tr.pop(loc, None)
            translations = merged_tr
        elif not use_force_merge:
            translations = merge_translation_bundle(
                existing_tr if isinstance(existing_tr, dict) else None,
                translations,
                source_title=spec["title"],
                source_description=spec.get("description"),
            )

        present = ", ".join(sorted(translations.keys())) or "(none)"
        print(f"  ✓ locales returned: {present}")
        if translations:
            additions.append((item, translations))
            if not args.dry_run:
                _persist_one(item, translations)

    if not additions:
        print("\nNo successful translations to write.", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"\n--dry-run set: would update {len(additions)} recipe(s).")
        print("Run again without --dry-run to write source files.")
        return 0
    touched = sorted({t.source_file.name for t, _ in additions})
    print(f"\nWrote translations for {len(additions)} recipe(s) into:")
    for name in touched:
        print(f"  - scripts/{name}")
    print("Review with:")
    print("  git diff scripts/")
    print("Then re-seed the live DB:")
    print("  uv run python -m scripts.seed_curated_recipes --quick")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
