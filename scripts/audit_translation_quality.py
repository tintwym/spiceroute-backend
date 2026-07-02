"""List curated recipes whose translation bundles look corrupt or incomplete."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `python scripts/audit_translation_quality.py` from repo root.
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.curated_data import CURATED
from scripts.translation_utils import (
    is_garbage_translation_text,
    is_stub_locale_bundle,
)

LOCALES = ("zh", "ja", "ko", "vi")


def bad_recipe_titles() -> list[str]:
    bad: set[str] = set()
    for recipe in CURATED:
        tr = recipe.get("translations") or {}
        for locale in LOCALES:
            bundle = tr.get(locale)
            if not isinstance(bundle, dict):
                bad.add(recipe["title"])
                break
            title = str(bundle.get("title") or "")
            desc = str(bundle.get("description") or "")
            if (
                is_stub_locale_bundle(
                    bundle,
                    source_title=recipe["title"],
                    source_description=recipe.get("description"),
                )
                or is_garbage_translation_text(title)
                or is_garbage_translation_text(desc)
            ):
                bad.add(recipe["title"])
                break
    return sorted(bad)


def main() -> int:
    titles = bad_recipe_titles()
    for title in titles:
        print(title)
    print(f"# {len(titles)} suspect recipe(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
