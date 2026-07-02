import uuid

from app.models.cuisine import Cuisine
from app.models.spice_route import Difficulty, SpiceRoute
from app.services.serialization import to_summary


def test_summary_collapses_myanmar_regional_to_burmese() -> None:
    row = SpiceRoute(
        id=uuid.uuid4(),
        title="Shan Khauk Swe",
        description="noodles",
        cuisine=Cuisine.SHAN,
        language="en",
        spice_level=1,
        prep_minutes=10,
        cook_minutes=20,
        servings=4,
        is_public=True,
        is_premium=False,
        difficulty=Difficulty.EASY,
    )
    summary = to_summary(row)
    assert summary.cuisine == Cuisine.BURMESE
