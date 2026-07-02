"""Remove garbage title/description keys from curated translation bundles."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.curated_data import CURATED
from scripts.translate_curated_recipes import (  # noqa: E402
    SOURCE_TARGETS,
    RecipeTarget,
    _find_recipe_dicts,
    _persist_one,
    _translations_line_range,
)
from scripts.translation_utils import is_garbage_translation_text  # noqa: E402


def _scrub_bundle(bundle: dict) -> dict:
    cleaned = dict(bundle)
    for field in ("title", "description"):
        val = cleaned.get(field)
        if isinstance(val, str) and is_garbage_translation_text(val, field=field):
            cleaned.pop(field, None)
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    spec_by_title = {spec["title"]: spec for spec in CURATED}
    touched = 0

    for source_file, list_name in SOURCE_TARGETS:
        if not source_file.is_file():
            continue
        source = source_file.read_text(encoding="utf-8")
        for title, node in _find_recipe_dicts(source, list_name=list_name):
            if _translations_line_range(node) is None:
                continue
            spec = spec_by_title.get(title)
            if spec is None:
                continue
            tr = spec.get("translations")
            if not isinstance(tr, dict):
                continue
            scrubbed: dict[str, dict] = {}
            changed = False
            for loc, bundle in tr.items():
                if not isinstance(bundle, dict):
                    continue
                next_bundle = _scrub_bundle(bundle)
                if next_bundle != bundle:
                    changed = True
                if next_bundle:
                    scrubbed[loc] = next_bundle
            if not changed:
                continue
            touched += 1
            print(f"  scrubbed {title!r}")
            if not args.dry_run:
                target = RecipeTarget(
                    source_file=source_file,
                    list_name=list_name,
                    title=title,
                    node=node,
                )
                _persist_one(target, scrubbed)

    print(f"Scrubbed {touched} recipe(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
