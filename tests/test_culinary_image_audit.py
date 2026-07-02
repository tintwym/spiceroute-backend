"""Tests for culinary image audit heuristics."""

from scripts.audit_culinary_images import _audit_recipe, _is_generic_unsplash
from scripts.fix_recipe_images import _slug_from_title


def test_generic_unsplash_is_fail():
    row = _audit_recipe(
        {
            "title": "Bulgogi",
            "description": "Sweet soy-marinated grilled beef.",
            "cuisine": "korean",
            "image": (
                "https://images.unsplash.com/photo-1551782450-a2132b4ba21d"
                "?w=1200&h=800&fit=crop&auto=format&q=80"
            ),
        }
    )
    assert row.verdict == "FAIL"
    assert "Unsplash" in row.reason


def test_wikimedia_bulgogi_filename_passes():
    row = _audit_recipe(
        {
            "title": "Bulgogi",
            "description": "Sweet soy-marinated grilled beef.",
            "cuisine": "korean",
            "image": (
                "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/"
                "Bulgogi_2.jpg/1280px-Bulgogi_2.jpg"
            ),
        }
    )
    assert row.verdict == "PASS"


def test_is_generic_unsplash_detects_hash_pool():
    slug = _slug_from_title("Pad Thai")
    from scripts.recipe_images import stable_food_image_url

    url = stable_food_image_url(slug)
    assert _is_generic_unsplash("Pad Thai", slug, url)
