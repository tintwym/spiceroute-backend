from app.services.locale_request import (
    locale_from_accept_language,
    requested_translation_locale,
)


def test_locale_from_accept_language_picks_first_supported():
    assert locale_from_accept_language("zh-CN,zh;q=0.9,en;q=0.8") == "zh"
    assert locale_from_accept_language("ja,en;q=0.5") == "ja"


def test_requested_translation_locale_prefers_query_param():
    assert (
        requested_translation_locale(
            translate_to="ko",
            accept_language="zh-CN,en",
        )
        == "ko"
    )


def test_requested_translation_locale_falls_back_to_accept_language():
    assert (
        requested_translation_locale(
            translate_to=None,
            accept_language="vi-VN,en",
        )
        == "vi"
    )
