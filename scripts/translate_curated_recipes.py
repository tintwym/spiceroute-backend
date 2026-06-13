"""Bulk-translate curated recipe titles + descriptions via Gemini.

ORTHOGONAL TO THE RUNTIME AI BACKEND. The app's user-facing AI Creator
and AI Companion now run on Ollama (see `app/services/ai/ollama.py`).
This script stays on Gemini purely because Gemini 2.5 Flash is meaningfully
better at low-resource multilingual translation (especially Burmese) than
the small open-weight models we deploy locally — and the script only runs
when we add new curated rows, which is rare.

`google-genai` is NOT in `pyproject.toml`'s runtime deps. Install it
on-demand in your local venv when you actually need to retranslate:

    uv pip install google-genai

Reads CURATED from `scripts/curated_data.py`, calls Gemini to translate
each recipe's title and description into the 5 non-English locales
SpiceRoute supports (zh, ja, ko, vi, my), and writes the resulting
`"translations": {...}` blocks back into `curated_data.py` in place —
preserving every line of the original file except the inserted blocks.

WHY THIS EXISTS
---------------
The Explore grid backs each card with a recipe row whose `title` and
`description` are static columns. Without per-locale overrides a Burmese
user viewing the seeded Quiche Lorraine card sees:

    Eyebrow:     ပြင်သစ်          (UI chrome, properly translated)
    Title:       Quiche Lorraine                  ← English leak
    Description: Buttery shortcrust filled…       ← English leak
    Time/yield:  ၁ နာရီ ၁၅ မိနစ်   (UI chrome, properly translated)

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

3. **One Gemini call per recipe.** The 5 locales come back together in
   a single structured-JSON response, so 33 recipes × 1 call ≈ 33
   calls. With Flash, ~$0.01 total. We could batch, but a single
   recipe per call gives us clean per-row error isolation and easy
   retry semantics.

4. **Burmese title fallback is intentional.** The prompt allows Gemini
   to return `"title": null` for Burmese when there's no settled
   transliteration of the dish name. The endpoint's
   `_resolve_translation` falls back to the source title (English) when
   the per-locale entry is missing or empty, so a `null` here yields
   the same UX as the hand-translated French recipes.

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
from pathlib import Path
from typing import Any

# Add the backend root to sys.path so we can `import scripts.curated_data`
# even when this script is invoked from the project root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.curated_data import CURATED  # noqa: E402

TARGET_LOCALES = ("zh", "ja", "ko", "vi", "my")

LOCALE_NAMES: dict[str, str] = {
    "zh": "Simplified Chinese (Mandarin)",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
    "my": "Burmese (Myanmar)",
}

CURATED_DATA_FILE = ROOT / "scripts" / "curated_data.py"


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

* TITLES — Internationally-recognized dish names (e.g. Sushi, Bibimbap,
  Pad Thai, Quiche Lorraine) should be TRANSLITERATED into the target
  script using the convention native speakers of that language actually
  use in cookbooks and menus (キッシュ・ロレーヌ for Japanese, 키슈 로렌
  for Korean, 红酒炖鸡 for Chinese-style descriptive titles, etc.).
* For Burmese (my): if no settled Burmese transliteration of the dish
  name exists, return null for the Burmese title. The app will fall
  back to the source title (the eyebrow already shows the cuisine in
  Burmese, so the card stays coherent). Only return a Burmese title
  string when you're confident it's the conventional rendering.
* DESCRIPTIONS — Translate faithfully and concisely. Keep the warm,
  inviting tone of food writing. Aim for similar length to the source.
  Use natural-sounding phrasing, not literal word-for-word translation.
* Use the target-language script throughout (no romanization mixed in
  unless the source had it).
* Do NOT add commentary, footnotes, or attribution.

Return ONLY a JSON object in exactly this shape (no markdown fences,
no surrounding prose, no trailing commas):

{{
  "zh": {{"title": "...", "description": "..."}},
  "ja": {{"title": "...", "description": "..."}},
  "ko": {{"title": "...", "description": "..."}},
  "vi": {{"title": "...", "description": "..."}},
  "my": {{"title": null, "description": "..."}}
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
    from google import genai
    from google.genai import types

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
    # Defensive shape check — drop any locales Gemini hallucinated
    # outside our supported set, and skip writing entries whose
    # description came back empty (a partial response is worse than
    # falling back to English).
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
        if out:
            cleaned[locale] = out
    return cleaned


# ---------------------------------------------------------------------------
# AST-driven source surgery
# ---------------------------------------------------------------------------


def _find_recipe_dicts(source: str) -> list[tuple[str, ast.Dict]]:
    """Return `(title, ast.Dict)` for every recipe in CURATED, in source
    order.

    Walks the module AST to locate the `CURATED = [...]` assignment and
    yields each list element. We need the AST node (not just the title
    string) so the caller can read `node.end_lineno` to know where to
    splice the translations block.
    """
    tree = ast.parse(source)
    curated_list: ast.List | None = None
    # `CURATED` is declared as `CURATED: list[RecipeSpec] = [...]` —
    # i.e. an *annotated* assignment, which is a separate AST node
    # from a plain `=` assignment. Match both shapes so future schema
    # refactors that drop the annotation don't silently break this
    # tool.
    for stmt in tree.body:
        if isinstance(stmt, ast.AnnAssign):
            if (
                isinstance(stmt.target, ast.Name)
                and stmt.target.id == "CURATED"
                and isinstance(stmt.value, ast.List)
            ):
                curated_list = stmt.value
                break
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "CURATED":
                    if isinstance(stmt.value, ast.List):
                        curated_list = stmt.value
                    break
            if curated_list is not None:
                break
    if curated_list is None:
        raise RuntimeError(
            "Couldn't locate `CURATED = [...]` in curated_data.py — "
            "did the schema change?"
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
            and getattr(v, "end_lineno", None) is not None
        ):
            return (k.lineno, v.end_lineno)
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
    title: str, translations: dict[str, dict[str, str]]
) -> None:
    """Re-parse curated_data.py, find the recipe dict whose title
    matches `title`, and splice in the freshly-translated block.

    Why re-parse on every write: the caller captured `ast.Dict` nodes
    from a single up-front parse. Once we write the first
    translation, every subsequent node's `lineno` is stale (every
    recipe BELOW the inserted block has shifted down by ~16 lines).
    Re-parsing each time gives us a stable view that already reflects
    the previous write.

    Why match by title (not lineno): the earlier "first node with
    lineno >= captured_lineno" approach has a subtle bug. Once
    enough prior recipes have been spliced, their fresh-parse
    linenos overtake the *original* linenos of later recipes — so
    the lookup for recipe N silently matches an earlier (already
    translated) recipe and re-writes its block instead. Manifested
    as "writes silently stop landing after ~recipe 13" in the
    backfill run that exposed this. Titles are unique within CURATED
    so they're a stable key.
    """
    src = CURATED_DATA_FILE.read_text(encoding="utf-8")
    fresh_nodes = _find_recipe_dicts(src)
    target: ast.Dict | None = None
    for fresh_title, node in fresh_nodes:
        if fresh_title == title:
            target = node
            break
    if target is None:
        print(
            f"  ! Warning: couldn't relocate recipe {title!r} for "
            f"incremental write; skipping persist",
            file=sys.stderr,
        )
        return
    new_src = _splice_translations(src, [(target, translations)])
    CURATED_DATA_FILE.write_text(new_src, encoding="utf-8")


def main() -> int:
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

    source = CURATED_DATA_FILE.read_text(encoding="utf-8")
    recipe_nodes = _find_recipe_dicts(source)

    # Decide which recipes need translation this run.
    to_translate: list[tuple[str, ast.Dict]] = []
    for title, node in recipe_nodes:
        if args.titles and title not in args.titles:
            continue
        if _has_translations(node) and not args.force:
            continue
        to_translate.append((title, node))

    if args.limit is not None:
        to_translate = to_translate[: args.limit]

    if not to_translate:
        print(
            "Nothing to translate. "
            "Pass --force to re-translate recipes that already have entries."
        )
        return 0

    print(f"Will translate {len(to_translate)} recipe(s):")
    for title, _ in to_translate:
        print(f"  - {title}")
    print()

    # Look the CURATED entry up by title to pull description / cuisine
    # without re-walking the AST.
    spec_by_title = {spec["title"]: spec for spec in CURATED}

    # Client-side rate-limit pacing. Free-tier gemini-2.5-flash allows
    # 5 requests/minute AND 20 requests/day (both ceilings apply).
    # --rpm=4 covers the per-minute side. The per-day ceiling can
    # ONLY be solved by upgrading to paid tier or waiting until
    # midnight Pacific — we just surface a clean 429 message in the
    # log when it triggers.
    #
    # The retry loop inside `_call_gemini` is a second line of
    # defence for the case where pacing isn't enough (concurrent
    # runs, model in high-demand mode, etc.).
    min_interval = 60.0 / args.rpm if args.rpm > 0 else 0.0
    last_call_at: float | None = None

    additions: list[tuple[ast.Dict, dict[str, dict[str, str]]]] = []
    for i, (title, node) in enumerate(to_translate, start=1):
        spec = spec_by_title[title]

        # Honour the per-minute budget BEFORE making the request, not
        # after — sleeping after the call would mean the first two
        # calls fire back-to-back and immediately trigger the 429.
        if last_call_at is not None and min_interval > 0:
            elapsed = time.monotonic() - last_call_at
            if elapsed < min_interval:
                wait = min_interval - elapsed
                # Only log the wait if it's noticeable (>1 s) — we
                # don't want to spam the operator with "sleeping 0.2s"
                # at 60 RPM on the paid tier.
                if wait > 1.0:
                    print(
                        f"  · pacing — sleeping {wait:.1f}s "
                        f"(--rpm={args.rpm:g})",
                        flush=True,
                    )
                time.sleep(wait)

        print(f"[{i}/{len(to_translate)}] {title} ({spec['cuisine']})…", flush=True)
        last_call_at = time.monotonic()
        try:
            translations = _call_gemini(
                title=title,
                description=spec["description"],
                cuisine=spec["cuisine"],
            )
        except Exception as exc:
            # Don't bail the whole run on a single failure — the rest of
            # the recipes are independent. Log it and continue.
            print(f"  ! Skipped: {exc}", file=sys.stderr)
            continue

        # Report what came back. A locale absent from the dict will
        # silently fall back to English on the live card.
        present = ", ".join(sorted(translations.keys())) or "(none)"
        print(f"  ✓ locales returned: {present}")
        if translations:
            additions.append((node, translations))
            # Persist incrementally — write after every successful
            # translation so a mid-run quota exhaustion / Ctrl-C /
            # crash doesn't lose work. We re-parse the file each
            # time so each splice operates on the freshly-written
            # source (otherwise the second write would clobber the
            # first because both AST nodes were captured from the
            # *original* parse). The trade-off is N file writes for
            # N translations, which is fine given the file is ~50 KB
            # and we're capped at 4 RPM anyway.
            if not args.dry_run:
                _persist_one(title, translations)

    if not additions:
        print("\nNo successful translations to write.", file=sys.stderr)
        return 1

    if args.dry_run:
        # In dry-run we never wrote per-iteration, so we splice all
        # at once just to validate the shape. Output is discarded.
        new_source = _splice_translations(source, additions)
        # `new_source` is intentionally unused — the splice is the
        # validation step in dry-run mode. Touching it here is just
        # so future-me doesn't "optimise" away the splice call by
        # accident.
        _ = new_source
        print(f"\n--dry-run set: would update {len(additions)} recipe(s).")
        print("Run again without --dry-run to write curated_data.py.")
        return 0
    print(
        f"\nWrote translations for {len(additions)} recipe(s) into "
        f"{CURATED_DATA_FILE.relative_to(ROOT)}."
    )
    print("Review with:")
    print(f"  git diff {CURATED_DATA_FILE.relative_to(ROOT)} | less")
    print("Then re-seed the live DB:")
    print("  python scripts/seed_curated_recipes.py --quick")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
