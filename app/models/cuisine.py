from enum import StrEnum


class Cuisine(StrEnum):
    """The 16 cuisines surfaced by the Explore tab.

    Keep the wire strings in sync with
    `spiceroute-flutter/lib/models/spice_route.dart` (`enum Cuisine`)
    and the cuisine pills in `lib/shared/cuisine_pill_bar.dart`. The
    AI recipe-generation JSON schema enum (see
    `app/services/ai/prompts.py`) must enumerate the same set.

    Declaration ORDER here is independent of any client-side display
    order — the Flutter enum defines its own ordering for the pill
    bar / filter dropdown, and the Postgres `cuisine_type` enum's
    internal ordinal is fixed by the order migrations appended the
    values (which is also independent of this declaration). Only the
    wire strings (the right-hand side of `=`) are load-bearing.

    Adding values is safe (append a new enum member AND run a new
    `ALTER TYPE cuisine_type ADD VALUE` migration; see
    `alembic/versions/0009_add_five_cuisines.py`). Removing or
    renaming an existing value requires a coordinated FE + BE + DB
    migration."""

    KOREAN = "korean"
    JAPANESE = "japanese"
    CHINESE = "chinese"
    BURMESE = "burmese"
    THAI = "thai"
    VIETNAMESE = "vietnamese"
    INDIAN = "indian"
    ITALIAN = "italian"
    AMERICAN_WESTERN = "american_western"
    MEXICAN = "mexican"
    FRENCH = "french"
    GREEK = "greek"
    SPANISH = "spanish"
    MALAYSIAN = "malaysian"
    GERMAN = "german"
    INDONESIAN = "indonesian"
