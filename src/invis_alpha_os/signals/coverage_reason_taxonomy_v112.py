"""Unified coverage reason taxonomy for candidate discovery (observation-only)."""

from __future__ import annotations

from enum import StrEnum


class CoverageReasonCodeV112(StrEnum):
    JP_CACHE_QUALITY = "jp_cache_quality_insufficient"
    US_DATA_QUALITY = "us_data_quality_insufficient"
    ETF_DATA_QUALITY = "etf_data_quality_insufficient"
    UNKNOWN = "unknown_coverage_gap"


COVERAGE_REASON_EN_BY_CODE_V112: dict[CoverageReasonCodeV112, str] = {
    CoverageReasonCodeV112.JP_CACHE_QUALITY: (
        "JP candidates were unavailable due to insufficient JP cache quality"
    ),
    CoverageReasonCodeV112.US_DATA_QUALITY: (
        "US equity candidates were unavailable due to insufficient data quality"
    ),
    CoverageReasonCodeV112.ETF_DATA_QUALITY: (
        "ETF proxy candidates were unavailable due to insufficient data quality"
    ),
}

COVERAGE_REASON_JA_BY_CODE_V112: dict[CoverageReasonCodeV112, str] = {
    CoverageReasonCodeV112.JP_CACHE_QUALITY: (
        "日本株候補は、キャッシュ品質不足のため候補抽出できませんでした。"
    ),
    CoverageReasonCodeV112.US_DATA_QUALITY: (
        "米国株候補は、データ品質不足のため候補抽出できませんでした。"
    ),
    CoverageReasonCodeV112.ETF_DATA_QUALITY: (
        "ETF proxy候補は、データ品質不足のため候補抽出できませんでした。"
    ),
    CoverageReasonCodeV112.UNKNOWN: "候補抽出に必要なデータ品質が不足しています。",
}

ENGLISH_NOTE_TO_CODE_V112: dict[str, CoverageReasonCodeV112] = {
    value: code for code, value in COVERAGE_REASON_EN_BY_CODE_V112.items()
}

NO_CANDIDATE_DEFAULT_REASON_JA_V112 = (
    "JP / US / ETF の横断候補が、データ品質・coverage・score条件を同時に満たしていません。"
)

JP_US_COMBINED_REASON_JA_V112 = (
    "日本株・米国株とも、候補判定に必要なデータ品質が不足していたため、"
    "強い新規候補として採用しませんでした。"
)


def parse_coverage_reason_codes_from_english(raw: str) -> tuple[CoverageReasonCodeV112, ...]:
    """Map slash-separated internal English notes to stable reason codes."""

    parts = [part.strip() for part in raw.split("/") if part.strip()]
    if not parts:
        return (CoverageReasonCodeV112.UNKNOWN,)
    codes: list[CoverageReasonCodeV112] = []
    for part in parts:
        codes.append(ENGLISH_NOTE_TO_CODE_V112.get(part, CoverageReasonCodeV112.UNKNOWN))
    return tuple(codes)


def translate_coverage_reason_codes_to_ja(codes: tuple[CoverageReasonCodeV112, ...]) -> str:
    """Render user-facing Japanese from stable coverage reason codes."""

    if not codes or codes == (CoverageReasonCodeV112.UNKNOWN,):
        return NO_CANDIDATE_DEFAULT_REASON_JA_V112
    if (
        CoverageReasonCodeV112.JP_CACHE_QUALITY in codes
        and CoverageReasonCodeV112.US_DATA_QUALITY in codes
    ):
        return JP_US_COMBINED_REASON_JA_V112
    return " / ".join(COVERAGE_REASON_JA_BY_CODE_V112[code] for code in codes)


def translate_user_facing_coverage_reason_to_ja(raw: str) -> str:
    """Convert internal English coverage notes to user-facing Japanese."""

    return translate_coverage_reason_codes_to_ja(parse_coverage_reason_codes_from_english(raw))
