"""Coverage for `compute_difficulty()` + the curated seed's
`_resolve_difficulty` override pipeline.

The auto-rule has three buckets and a couple of tie-break axes, so
this file walks the boundaries explicitly rather than relying on a
parametrize block — each row reads as a sentence ("a 30-minute,
5-step recipe is EASY") which makes a future regression on the
thresholds easy to diff in code review.
"""
import pytest

from app.models.difficulty import Difficulty, compute_difficulty

# ---------------------------------------------------------------------------
# `compute_difficulty` — the rule the user's brief defined.
# ---------------------------------------------------------------------------


def test_short_clock_few_steps_is_easy():
    # The textbook EASY case: 30 minutes total, 4 steps.
    assert compute_difficulty(prep_minutes=10, cook_minutes=20, step_count=4) == (
        Difficulty.EASY
    )


def test_easy_max_total_is_exclusive():
    # 45 minutes is NOT EASY — the rule says strictly less than 45.
    # This pins the boundary so a future "let's say <= 45" tweak shows up
    # as a deliberate diff to this assertion.
    assert compute_difficulty(prep_minutes=15, cook_minutes=30, step_count=5) == (
        Difficulty.MEDIUM
    )


def test_easy_step_ceiling():
    # 6 steps is the inclusive ceiling for EASY (the curated catalog's
    # convention is ~6 steps per recipe; tighter would needlessly push
    # 30-min/6-step dishes into MEDIUM and confuse users).
    assert compute_difficulty(prep_minutes=10, cook_minutes=20, step_count=6) == (
        Difficulty.EASY
    )
    # One more step and the same clock crosses into MEDIUM.
    assert compute_difficulty(prep_minutes=10, cook_minutes=20, step_count=7) == (
        Difficulty.MEDIUM
    )


def test_medium_window():
    # MEDIUM owns 45 ≤ total ≤ 120 with sub-HARD step counts.
    assert compute_difficulty(prep_minutes=20, cook_minutes=40, step_count=6) == (
        Difficulty.MEDIUM
    )
    assert compute_difficulty(prep_minutes=30, cook_minutes=90, step_count=6) == (
        Difficulty.MEDIUM
    )


def test_total_over_two_hours_is_hard():
    # 121 minutes is just over the MEDIUM ceiling — HARD.
    assert compute_difficulty(prep_minutes=1, cook_minutes=120, step_count=4) == (
        Difficulty.HARD
    )
    # The user's reference: Taiwanese Beef Noodle Soup at ~205 min.
    assert compute_difficulty(prep_minutes=25, cook_minutes=180, step_count=6) == (
        Difficulty.HARD
    )


def test_many_steps_is_hard_even_when_short():
    # Step-count proxy for "highly technical, multi-phase" — a 30-min
    # recipe with 11 steps is HARD even though the clock is short.
    assert compute_difficulty(prep_minutes=10, cook_minutes=20, step_count=11) == (
        Difficulty.HARD
    )


def test_negative_inputs_are_clamped_to_zero():
    # The signature doesn't constrain prep/cook to non-negative; a
    # buggy caller passing -5 shouldn't crash the API. Behaviour:
    # treat negatives as zero and return the result for the clamped
    # values.
    assert compute_difficulty(prep_minutes=-5, cook_minutes=-10, step_count=-3) == (
        Difficulty.EASY
    )


def test_wire_strings_are_load_bearing():
    # The wire format is contract with both the Postgres enum and the
    # Flutter `Difficulty.fromWire`. Renaming these requires a
    # coordinated migration + FE/BE deploy, so pin them here.
    assert Difficulty.EASY.value == "easy"
    assert Difficulty.MEDIUM.value == "medium"
    assert Difficulty.HARD.value == "hard"


# ---------------------------------------------------------------------------
# `_resolve_difficulty` — curated overrides + spec pinning.
# ---------------------------------------------------------------------------


def test_resolve_uses_spec_pinned_value_first():
    from scripts.seed_curated_recipes import _resolve_difficulty

    # When the spec pins "hard", the resolver MUST honour it even if
    # the auto-rule would say something else. This is the escape hatch
    # for the rare recipe where neither the per-title override nor the
    # rule gets it right (e.g. a future spec we haven't audited).
    spec = {
        "title": "Test Dish",
        "prep": 5,
        "cook": 5,
        "steps": ["a", "b"],
        "difficulty": "hard",
    }
    assert _resolve_difficulty(spec) == Difficulty.HARD


def test_resolve_uses_per_title_override_when_no_pin():
    from scripts.seed_curated_recipes import _resolve_difficulty

    # Baklava is the canonical override case — the auto-rule says
    # MEDIUM (80 min, 6 steps) but the user's rules call out
    # "highly technical pastry" as HARD.
    spec = {
        "title": "Baklava",
        "prep": 20,
        "cook": 60,
        "steps": ["a"] * 6,
    }
    assert _resolve_difficulty(spec) == Difficulty.HARD


def test_resolve_falls_back_to_rule_when_no_override():
    from scripts.seed_curated_recipes import _resolve_difficulty

    # A recipe with neither a spec pin nor an override-by-title gets
    # the rule-based value — keeps the bulk of the catalog working
    # without explicit per-row annotations.
    spec = {
        "title": "Some New Dish Not In Override Map",
        "prep": 10,
        "cook": 20,
        "steps": ["a"] * 4,
    }
    assert _resolve_difficulty(spec) == Difficulty.EASY


def test_resolve_rejects_invalid_pinned_value():
    from scripts.seed_curated_recipes import _resolve_difficulty

    # Spec authors who type "EASY" / "Hard" / "expert" should see a
    # loud failure at seed time, not a silent fallback to MEDIUM. The
    # StrEnum constructor raises ValueError on unknown strings, which
    # is exactly the behaviour we want.
    spec = {
        "title": "Bad Spec",
        "prep": 5,
        "cook": 5,
        "steps": [],
        "difficulty": "expert",
    }
    with pytest.raises(ValueError):
        _resolve_difficulty(spec)
