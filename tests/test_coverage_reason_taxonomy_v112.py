from __future__ import annotations

from invis_alpha_os.signals.coverage_reason_taxonomy_v112 import (
    CoverageReasonCodeV112,
    parse_coverage_reason_codes_from_english,
    translate_coverage_reason_codes_to_ja,
    translate_user_facing_coverage_reason_to_ja,
)


def test_parse_coverage_reason_codes_from_english_maps_known_notes() -> None:
    raw = (
        "JP candidates were unavailable due to insufficient JP cache quality / "
        "US equity candidates were unavailable due to insufficient data quality"
    )
    codes = parse_coverage_reason_codes_from_english(raw)
    assert codes == (
        CoverageReasonCodeV112.JP_CACHE_QUALITY,
        CoverageReasonCodeV112.US_DATA_QUALITY,
    )


def test_translate_user_facing_coverage_reason_to_ja_combines_jp_us() -> None:
    raw = (
        "JP candidates were unavailable due to insufficient JP cache quality / "
        "US equity candidates were unavailable due to insufficient data quality"
    )
    translated = translate_user_facing_coverage_reason_to_ja(raw)
    assert "日本株・米国株とも" in translated
    assert "JP candidates" not in translated


def test_translate_coverage_reason_codes_to_ja_unknown_fallback() -> None:
    translated = translate_coverage_reason_codes_to_ja((CoverageReasonCodeV112.UNKNOWN,))
    assert "JP / US / ETF" in translated
