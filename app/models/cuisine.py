from enum import StrEnum


class Cuisine(StrEnum):
    """The 11 cuisines surfaced by the Explore tab.

    Keep this list in sync with `spiceroute-flutter/lib/models/cuisine.dart`
    and the cuisine pills in `lib/shared/cuisine_pill_bar.dart`."""

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
