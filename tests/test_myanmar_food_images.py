"""Tests for Myanmar recipe image curation."""

import time

import pytest

from scripts.generate_myanmar_expansion import _DISHES
from scripts.myanmar_food_images import MYANMAR_WIKIMEDIA_BY_SLUG
from scripts.recipe_images import image_url_is_alive


def test_every_myanmar_expansion_slug_has_wikimedia_image():
    slugs = {slug for _wire, slug, _title, *_rest in _DISHES}
    missing = slugs - set(MYANMAR_WIKIMEDIA_BY_SLUG)
    assert not missing, f"Missing Myanmar images for slugs: {sorted(missing)}"


@pytest.mark.network
def test_myanmar_wikimedia_urls_are_alive():
    unique = sorted(set(MYANMAR_WIKIMEDIA_BY_SLUG.values()))
    dead: list[str] = []
    for url in unique:
        if not image_url_is_alive(url, retries=3):
            dead.append(url[:80])
        time.sleep(0.35)
    assert not dead, f"Dead Myanmar image URLs: {dead}"
