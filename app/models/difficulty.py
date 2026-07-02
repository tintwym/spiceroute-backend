"""Difficulty enum and a single source of truth for the auto-computed
difficulty fallback used by user-created and AI-generated recipes.

The enum is a first-class column on `spice_routes` (see
`alembic/versions/0012_add_difficulty.py`); curated rows are hand-labelled
in `scripts/curated_data.py` and other rows derive their value from
[`compute_difficulty`] at save time.

Rules (mirroring the product PRD):

  - EASY    -> total time < 45 min AND minimal step count (< 6)
  - MEDIUM  -> total time 45–120 min OR moderate step count (6–9)
  - HARD    -> total time > 120 min OR step count >= 10 (proxy for
                multi-phase technical recipes like braises and pastries)

The step-count cutoffs are heuristics, not laws of physics. They exist
so that a "30 min recipe with 11 steps" (e.g. a fast but
technique-heavy plated dish) doesn't get flagged EASY just because the
clock is short.
"""

from enum import StrEnum


class Difficulty(StrEnum):
    """How challenging a recipe is to execute.

    Wire strings ("easy" / "medium" / "hard") are load-bearing — they're
    what Postgres' `difficulty_type` enum stores, what the API returns,
    and what the Flutter `Difficulty` enum's `wire` getter parses on the
    way in. Renaming a value requires a coordinated migration plus an
    FE + BE deploy in lockstep.
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# Step-count thresholds. Step count is a coarse proxy for technical
# complexity (a 14-step recipe is almost certainly multi-phase even if
# its clock is short); time is the primary axis and steps are the
# tiebreaker. Tuned against the curated catalog (where the seed
# convention is roughly 6 steps per recipe) and the user's reference
# set:
#
#   Tabbouleh        ~30 min,  6 steps  -> EASY    (< 45 AND <= 6)
#   Chicken Adobo    ~55 min,  6 steps  -> MEDIUM  (45 ≤ total ≤ 120)
#   Sauerbraten      ~3+ hr,   6 steps  -> HARD    (total > 120)
#   Baklava          ~80 min,  pastry   -> HARD    (overridden per-title
#                                                   in scripts/curated_data
#                                                   for the technical-pastry
#                                                   exception in the rules)
_EASY_MAX_TOTAL_MIN = 45
_MEDIUM_MAX_TOTAL_MIN = 120
_HARD_MIN_STEPS = 10
_EASY_MAX_STEPS = 6


def compute_difficulty(
    *,
    prep_minutes: int,
    cook_minutes: int,
    step_count: int,
) -> Difficulty:
    """Deterministic auto-computation from the rules above. Used as the
    fallback for user-created / AI-generated recipes whose author
    didn't pin an explicit value. Curated rows ship their own
    hand-labelled `difficulty` and skip this entirely.

    Designed to be cheap (no I/O), pure (same inputs → same output),
    and total (always returns one of the three enum values, never
    raises) so it's safe to call from a request handler on the
    write path.
    """
    total = max(0, prep_minutes) + max(0, cook_minutes)
    steps = max(0, step_count)

    # HARD trumps everything else — a very long recipe OR a very
    # step-heavy one is HARD regardless of the other axis.
    if total > _MEDIUM_MAX_TOTAL_MIN or steps >= _HARD_MIN_STEPS:
        return Difficulty.HARD
    # EASY requires BOTH a short clock AND a low step count. The
    # "AND" matters: a 20-minute recipe with 8 steps is not "easy"
    # in the sense the chip implies; it's a "quick but fiddly" dish
    # that earns MEDIUM.
    if total < _EASY_MAX_TOTAL_MIN and steps <= _EASY_MAX_STEPS:
        return Difficulty.EASY
    return Difficulty.MEDIUM
