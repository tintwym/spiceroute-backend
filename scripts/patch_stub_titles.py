"""Patch curated recipe titles that still equal the English source string."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.curated_data import CURATED  # noqa: E402
from scripts.translate_curated_recipes import (  # noqa: E402
    SOURCE_TARGETS,
    RecipeTarget,
    _collect_translation_targets,
    _find_recipe_dicts,
    _persist_one,
)
from scripts.translation_utils import is_stub_locale_bundle  # noqa: E402

# (recipe title, locale) -> localized title (must differ from English source)
TITLE_FIXES: dict[tuple[str, str], str] = {
    ("Moussaka", "vi"): "Mousaka kiểu Hy Lạp",
    ("Feijoada", "vi"): "Món đậu đen Brazil",
    ("Lomo Saltado", "vi"): "Thịt bò xào kiểu Peru",
    ("Bacalhau à Brás", "vi"): "Cá tuyết xào trứng khoai tây",
    ("Tsuivan", "vi"): "Mì xào Tsuivan Mông Cổ",
    ("Xiaolongbao", "vi"): "Bánh bao tiểu long",
    ("Samsa", "vi"): "Bánh Samsa nướng",
    ("Rafute", "vi"): "Thịt heo Rafute Okinawa",
    ("Roujiamo", "vi"): "Bánh mì kẹp thịt Tây An",
    ("Bulgogi", "vi"): "Thịt bò Bulgogi nướng",
    ("Tonkatsu", "zh"): "日式炸猪排",
    ("Tonkatsu", "ja"): "とんかつ",
    ("Tonkatsu", "ko"): "돈가스",
    ("Tonkatsu", "vi"): "Thịt heo tonkatsu chiên xù",
    ("Zaalouk", "vi"): "Salad cà tím Zaalouk",
    ("Tibs", "vi"): "Thịt bò Tibs Ethiopia",
    ("Shiro Wat", "vi"): "Hầm đậu tương Shiro",
    ("Kare-Kare", "vi"): "Kare-kare thịt bò Philippines",
    ("Chapli Kebab", "vi"): "Kebab Chapli Pakistan",
    ("Kottu Roti", "vi"): "Bánh roti xào Sri Lanka",
    ("Aji de Gallina", "vi"): "Gà sốt ớt vàng Peru",
    ("Hinny Paw", "vi"): "Bánh Hinny Paw Shan",
    ("Kachin Singju", "vi"): "Gỏi Kachin Singju",
}


def main() -> int:
    spec_by_title = {r["title"]: r for r in CURATED}
    targets = {
        t.title: t
        for t in _collect_translation_targets(force=True, repair=False, titles=None)
    }

    patched: list[tuple[RecipeTarget, dict]] = []
    for (title, locale), new_title in TITLE_FIXES.items():
        spec = spec_by_title.get(title)
        if spec is None:
            print(f"! missing spec: {title}", file=sys.stderr)
            continue
        tr = dict(spec.get("translations") or {})
        bundle = dict(tr.get(locale) or {})
        if not bundle:
            print(f"! missing bundle: {title} {locale}", file=sys.stderr)
            continue
        bundle["title"] = new_title
        tr[locale] = bundle
        spec["translations"] = tr
        if is_stub_locale_bundle(
            bundle,
            source_title=title,
            source_description=spec.get("description"),
        ):
            print(f"! still stub after fix: {title} {locale}", file=sys.stderr)
            continue
        target = targets.get(title)
        if target is None:
            print(f"! no source target: {title}", file=sys.stderr)
            continue
        patched.append((target, tr))
        print(f"✓ {title} [{locale}] -> {new_title}")

    seen: set[str] = set()
    for target, tr in patched:
        if target.title in seen:
            continue
        seen.add(target.title)
        _persist_one(target, tr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
