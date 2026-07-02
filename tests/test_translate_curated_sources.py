"""Smoke tests for multi-file curated translation tooling."""

from __future__ import annotations

from scripts.translate_curated_recipes import (
    SOURCE_TARGETS,
    _collect_translation_targets,
    _find_recipe_dicts,
)


def test_expansion_modules_expose_recipe_dicts() -> None:
    for source_file, list_name in SOURCE_TARGETS:
        if list_name == "CURATED":
            continue
        source = source_file.read_text(encoding="utf-8")
        nodes = _find_recipe_dicts(source, list_name=list_name)
        assert nodes, f"{source_file.name} should contain recipes in {list_name}"


def test_collect_translation_targets_includes_expansion_without_translations() -> None:
    targets = _collect_translation_targets(force=False, repair=False, titles=None)
    files = {t.source_file.name for t in targets}
    assert "cuisine_expansion_v5_east_asia.py" in files or len(targets) == 0
