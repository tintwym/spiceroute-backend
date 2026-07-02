from enum import StrEnum


class Cuisine(StrEnum):
    """The 76 cuisines surfaced by the Explore tab.

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
    `alembic/versions/0011_add_v4_cuisines.py` for the most recent
    example). Removing or renaming an existing value requires a
    coordinated FE + BE + DB migration."""

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
    # v4 Phase 1 — fill empty / sparse regions.
    LEBANESE = "lebanese"
    TURKISH = "turkish"
    MOROCCAN = "moroccan"
    ETHIOPIAN = "ethiopian"
    FILIPINO = "filipino"
    PAKISTANI = "pakistani"
    SRI_LANKAN = "sri_lankan"
    CAMBODIAN = "cambodian"
    # v4 Phase 2 — opportunistic expansion + umbrella cuisines.
    BRAZILIAN = "brazilian"
    PERUVIAN = "peruvian"
    CARIBBEAN = "caribbean"
    TAIWANESE = "taiwanese"
    PORTUGUESE = "portuguese"
    BRITISH = "british"
    # Retired from the product catalog (v8) but kept here so ORM loads
    # legacy Postgres rows until a re-seed/migration removes them.
    # Without this member, `/spice_routes` 500s when any row still
    # carries `cuisine_type = eastern_european`.
    EASTERN_EUROPEAN = "eastern_european"
    # v5 — East Asia regional expansion.
    MONGOLIAN = "mongolian"
    TIBETAN = "tibetan"
    HONG_KONG = "hong_kong"
    MACANESE = "macanese"
    SICHUAN = "sichuan"
    CANTONESE = "cantonese"
    SHANGHAINESE = "shanghainese"
    FUJIAN = "fujian"
    HUNAN = "hunan"
    YUNNAN = "yunnan"
    BEIJING = "beijing"
    DONGBEI = "dongbei"
    HAKKA = "hakka"
    UYGHUR = "uyghur"
    OKINAWAN = "okinawan"
    SHANDONG = "shandong"
    GUANGXI = "guangxi"
    TEOCHEW = "teochew"
    HAINANESE = "hainanese"
    JIANGSU = "jiangsu"
    ZHEJIANG = "zhejiang"
    ANHUI = "anhui"
    JIANGXI = "jiangxi"
    GUIZHOU = "guizhou"
    MANCHURIAN = "manchurian"
    SHAANXI = "shaanxi"
    # v7 — Myanmar regional expansion.
    SHAN = "shan"
    RAKHINE = "rakhine"
    MON = "mon"
    KACHIN = "kachin"
    KAYIN = "kayin"
    CHIN = "chin"
    KAYAH = "kayah"
    MANDALAY = "mandalay"
    YANGON = "yangon"
    AYEYARWADY = "ayeyarwady"
    TANINTHARYI = "tanintharyi"
    INTHA = "intha"
    NAGA = "naga"
    PA_O = "pa_o"
    DANU = "danu"
    WA = "wa"
    MAGWAY = "magway"
    BAGO = "bago"
    SAGAING = "sagaing"
    TAUNGGYI = "taunggyi"
