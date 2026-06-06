from __future__ import annotations

from invis_alpha_os.product.weekly_candidate_brief_v0 import (
    WeeklyCandidateBriefV0,
    format_weekly_candidate_brief_v0_copy,
    translate_user_facing_coverage_reason_to_ja,
)

FIXTURE_CANDIDATE_NAMES = ("GRID_A", "ROBO_B", "MAT_C", "CASH_D", "HYPE_E")
FORBIDDEN_TRADING_PHRASES = ("今すぐ購入", "注文実行", "買うべき", "売るべき")


def _zero_candidate_brief() -> WeeklyCandidateBriefV0:
    return WeeklyCandidateBriefV0(
        report_date="2026-06-02",
        generated_at_jp="fixture-only",
        generated_at_us="fixture-only",
        jp_scope="fixture-only",
        us_scope="fixture-only",
        macro_summary="fixture-only trial",
        coverage_note=(
            "coverage_note: JP candidates were unavailable due to insufficient JP cache quality / "
            "US equity candidates were unavailable due to insufficient data quality"
        ),
    )


def test_zero_candidate_weekly_copy_readability_contract() -> None:
    body = format_weekly_candidate_brief_v0_copy(_zero_candidate_brief())

    assert "## 今週の結論（3行）" in body
    assert "初動候補は0件" in body
    assert "## 開発者向け集計" in body
    assert "## ポートフォリオ制約" in body
    assert "## 用語・安全注記" in body
    assert "これは売買指示ではありません" in body

    for fixture_name in FIXTURE_CANDIDATE_NAMES:
        assert fixture_name not in body.split("## 開発者向け集計")[0]

    assert "JP candidates were unavailable" not in body
    assert "insufficient JP cache quality" not in body

    for phrase in FORBIDDEN_TRADING_PHRASES:
        assert phrase not in body


def test_translate_user_facing_coverage_reason_to_ja_maps_known_notes() -> None:
    raw = (
        "coverage_note: JP candidates were unavailable due to insufficient JP cache quality / "
        "US equity candidates were unavailable due to insufficient data quality"
    )
    ja = translate_user_facing_coverage_reason_to_ja(raw)
    assert "データ品質" in ja
    assert "米国株" in ja
