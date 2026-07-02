import urllib.request

import pytest

from scripts.fix_recipe_images import resolve_recipe_image_url
from scripts.recipe_images import _UNSPLASH_FOOD_PHOTOS, stable_food_image_url


@pytest.mark.network
def test_all_unsplash_ids_are_alive():
    for photo_id in _UNSPLASH_FOOD_PHOTOS:
        url = f"https://images.unsplash.com/{photo_id}?w=400&h=300&fit=crop&auto=format"
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as resp:
            assert resp.status == 200, photo_id


def test_stable_food_image_url_is_deterministic():
    a = stable_food_image_url("tea-shop-eggs")
    b = stable_food_image_url("tea-shop-eggs")
    assert a == b
    assert "images.unsplash.com" in a


def test_resolve_recipe_image_url_dedupes_unsplash_fallback():
    """Generic Unsplash pool URLs stay unique; Wikimedia may be shared."""
    from scripts.recipe_images import stable_food_image_url

    assigned = {stable_food_image_url("not-in-curated-dish")}
    url = resolve_recipe_image_url("Totally Unknown Dish XYZ", assigned_urls=assigned)
    assert url not in assigned
    assert "images.unsplash.com" in url


def test_myanmar_titles_may_share_wikimedia_image():
    """Myanmar curated URLs are shared by design — dedup must not force Unsplash."""
    assigned: set[str] = set()
    first = resolve_recipe_image_url("Shan Noodles", assigned_urls=assigned)
    second = resolve_recipe_image_url("Shan Khauk Swe", assigned_urls=assigned)
    assert "wikimedia.org" in first
    assert first == second
