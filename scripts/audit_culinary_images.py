"""Culinary accuracy audit for recipe card images.

Checks every curated recipe against the audit rules:
  - Generic Unsplash pool photos are automatic FAIL (not dish-matched).
  - Wikimedia hand-curated photos PASS when the filename or article
    plausibly depicts the titled dish.
  - Cross-cuisine duplicate Unsplash URLs are flagged FAIL.

Usage:
    uv run python -m scripts.audit_culinary_images
    uv run python -m scripts.audit_culinary_images --json report.json
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path

from scripts.curated_data import _WIKIMEDIA_IMAGE_BY_SLUG, CURATED
from scripts.fix_recipe_images import _slug_from_title
from scripts.recipe_images import stable_food_image_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("culinary_audit")

# Protein / base tokens we expect to see in image filenames for meat/fish dishes.
_PROTEIN_HINTS = {
    "beef": ("beef", "steak", "cow", "brisket", "rib"),
    "chicken": ("chicken", "poultry", "gallina", "gai"),
    "pork": ("pork", "bacon", "ham", "char siu", "charsiu", "rou"),
    "fish": ("fish", "salmon", "tuna", "ceviche", "cebiche", "carp"),
    "shrimp": ("shrimp", "prawn", "goong", "kung"),
    "lamb": ("lamb", "mutton"),
    "duck": ("duck", "peking"),
    "tofu": ("tofu", "doufu"),
    "egg": ("egg", "omelette", "omelet"),
}


@dataclass
class AuditRow:
    title: str
    cuisine: str
    slug: str
    image: str
    verdict: str  # PASS | FAIL | REVIEW
    reason: str


def _is_generic_unsplash(title: str, slug: str, image: str) -> bool:
    return image == stable_food_image_url(slug) or (
        "images.unsplash.com" in image and slug not in _WIKIMEDIA_IMAGE_BY_SLUG
    )


def _filename_from_url(url: str) -> str:
    path = urllib.parse.unquote(url.split("/")[-1]).lower()
    return re.sub(r"\.[a-z]+$", "", path).replace("_", " ").replace("-", " ")


def _description_proteins(description: str, title: str) -> set[str]:
    blob = f"{title} {description}".lower()
    found: set[str] = set()
    for protein, hints in _PROTEIN_HINTS.items():
        if protein in blob or any(h in blob for h in hints):
            found.add(protein)
    return found


def _audit_recipe(spec: dict) -> AuditRow:
    title = spec["title"]
    cuisine = spec["cuisine"]
    description = spec.get("description", "")
    slug = _slug_from_title(title)
    image = spec["image"]

    if _is_generic_unsplash(title, slug, image):
        return AuditRow(
            title=title,
            cuisine=cuisine,
            slug=slug,
            image=image,
            verdict="FAIL",
            reason="Generic Unsplash pool photo — not matched to dish title or cuisine",
        )

    if "unsplash.com" in image.lower():
        return AuditRow(
            title=title,
            cuisine=cuisine,
            slug=slug,
            image=image,
            verdict="FAIL",
            reason="Generic Unsplash pool photo — not matched to dish title or cuisine",
        )

    if "wikimedia.org" not in image.lower():
        return AuditRow(
            title=title,
            cuisine=cuisine,
            slug=slug,
            image=image,
            verdict="FAIL",
            reason="Non-curated image host",
        )

    fname = _filename_from_url(image)
    slug_words = set(slug.replace("-", " ").split())
    title_words = {w.lower() for w in re.findall(r"[a-z]{4,}", title.lower())}

    # Strong pass when filename echoes dish tokens.
    if slug_words & set(fname.split()) or title_words & set(fname.split()):
        return AuditRow(
            title=title,
            cuisine=cuisine,
            slug=slug,
            image=image,
            verdict="PASS",
            reason="Wikimedia photo filename matches dish",
        )

    # Soft heuristic: protein in description should appear in filename.
    proteins = _description_proteins(description, title)
    if proteins:
        fname_blob = fname
        if not any(
            h in fname_blob
            for protein in proteins
            for h in _PROTEIN_HINTS.get(protein, (protein,))
        ):
            return AuditRow(
                title=title,
                cuisine=cuisine,
                slug=slug,
                image=image,
                verdict="REVIEW",
                reason=f"Wikimedia photo may not show expected protein(s): {', '.join(sorted(proteins))}",
            )

    return AuditRow(
        title=title,
        cuisine=cuisine,
        slug=slug,
        image=image,
        verdict="PASS",
        reason="Hand-curated Wikimedia URL",
    )


def run_audit() -> list[AuditRow]:
    rows = [_audit_recipe(spec) for spec in CURATED]

    # Flag duplicate Unsplash URLs across different cuisines.
    by_url: dict[str, list[AuditRow]] = {}
    for row in rows:
        if "unsplash.com" in row.image:
            by_url.setdefault(row.image, []).append(row)

    for _url, group in by_url.items():
        cuisines = {r.cuisine for r in group}
        if len(cuisines) > 1:
            for row in group:
                if row.verdict == "PASS":
                    row.verdict = "FAIL"
                    row.reason = (
                        "Same generic Unsplash photo shared across cuisines: "
                        + ", ".join(sorted(cuisines))
                    )
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json", type=Path, help="Write full report JSON here")
    args = p.parse_args(argv)

    rows = run_audit()
    passed = sum(1 for r in rows if r.verdict == "PASS")
    failed = sum(1 for r in rows if r.verdict == "FAIL")
    review = sum(1 for r in rows if r.verdict == "REVIEW")

    log.info(
        "recipes=%d pass=%d fail=%d review=%d",
        len(rows),
        passed,
        failed,
        review,
    )

    for row in rows:
        if row.verdict == "FAIL":
            log.warning("%s [%s] — %s", row.title, row.cuisine, row.reason)

    for row in rows:
        if row.verdict == "REVIEW":
            log.info("REVIEW %s — %s", row.title, row.reason)

    if args.json:
        args.json.write_text(
            json.dumps([asdict(r) for r in rows], indent=2),
            encoding="utf-8",
        )
        log.info("wrote %s", args.json)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
