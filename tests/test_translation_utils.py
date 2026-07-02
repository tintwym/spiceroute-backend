from scripts.translation_utils import (
    is_garbage_translation_text,
    is_stub_locale_bundle,
    merge_translation_bundle,
    strip_stub_bundles,
)


def test_is_garbage_detects_stripped_vietnamese_debris() -> None:
    assert is_garbage_translation_text("Ch", field="title")
    assert is_garbage_translation_text(
        "Ch tr m t v ng v th c m", field="description"
    )
    assert is_garbage_translation_text(
        "주울었하세요 주울었하세요 주울었하세요", field="description"
    )
    assert not is_garbage_translation_text("叉烧", field="title")
    assert not is_garbage_translation_text("煎饼", field="title")


def test_is_stub_locale_bundle_detects_english_copy() -> None:
    bundle = {
        "title": "Jianbing",
        "description": "Crispy crepe with egg, cracker, and sauces.",
    }
    assert is_stub_locale_bundle(
        bundle,
        source_title="Jianbing",
        source_description="Crispy crepe with egg, cracker, and sauces.",
    )


def test_is_stub_locale_bundle_accepts_real_translation() -> None:
    bundle = {
        "title": "煎饼",
        "description": "香脆蛋饼，配薄脆和酱料。",
    }
    assert not is_stub_locale_bundle(
        bundle,
        source_title="Jianbing",
        source_description="Crispy crepe with egg, cracker, and sauces.",
    )


def test_merge_replaces_stub_title_but_keeps_polished_copy() -> None:
    existing = {
        "zh": {
            "title": "Risotto alla Milanese",
            "description": "Saffron risotto finished with butter and parmesan.",
            "ingredients": ["a"],
        }
    }
    fresh = {
        "zh": {
            "title": "米兰烩饭",
            "description": "藏红花烩饭，以黄油和帕玛森收尾。",
            "ingredients": ["甲"],
        }
    }
    merged = merge_translation_bundle(
        existing,
        fresh,
        source_title="Risotto alla Milanese",
        source_description="Saffron risotto finished with butter and parmesan.",
    )
    assert merged["zh"]["title"] == "米兰烩饭"
    assert merged["zh"]["description"] == "藏红花烩饭，以黄油和帕玛森收尾。"
    assert merged["zh"]["ingredients"] == ["甲"]


def test_merge_preserves_hand_polished_title() -> None:
    existing = {"zh": {"title": "泡菜汤", "description": "暖心汤。"}}
    fresh = {"zh": {"title": "Different LLM title", "description": "Different"}}
    merged = merge_translation_bundle(
        existing,
        fresh,
        source_title="Kimchi Jjigae",
        source_description="Warm stew.",
    )
    assert merged["zh"]["title"] == "泡菜汤"
    assert merged["zh"]["description"] == "暖心汤。"


def test_strip_stub_bundles_removes_english_keys() -> None:
    raw = {
        "zh": {
            "title": "Jianbing",
            "description": "Crispy crepe.",
            "ingredients": ["x"],
        }
    }
    cleaned = strip_stub_bundles(
        raw,
        source_title="Jianbing",
        source_description="Crispy crepe.",
    )
    assert cleaned == {"zh": {"ingredients": ["x"]}}
