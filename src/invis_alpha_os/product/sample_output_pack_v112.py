"""Fixture-only sample output pack for stdout regeneration (no file writes)."""

from __future__ import annotations

from invis_alpha_os.product.portfolio_data_quality_review_v109 import (
    build_portfolio_data_quality_review_v109,
    render_portfolio_data_quality_review_markdown_v109,
)
from invis_alpha_os.product.raw_input_quarantine_review_v111 import (
    build_portfolio_quarantine_cross_review_v111,
    render_portfolio_quarantine_cross_review_markdown_v111,
)
from invis_alpha_os.product.raw_input_quarantine_v110 import (
    QuarantineSourceKind,
    RawInputQuarantineManifestV110,
    render_raw_input_quarantine_review_markdown_v110,
    review_raw_input_quarantine_manifest_v110,
)

_SAMPLE_DISCLAIMER = (
    "> このサンプルは source-only / fixture-only の出力例です。\n"
    "> 実データの正確性・鮮度を保証せず、売買指示ではありません。\n"
    "> actual import / cache write / broker API / raw Excel parsing は実行していません。"
)


def _safe_fixture_manifest_v110() -> RawInputQuarantineManifestV110:
    return RawInputQuarantineManifestV110(
        source_kind=QuarantineSourceKind.FIXTURE,
        declared_unit="man_yen",
        declared_currency="JPY",
        statement_month="2026-05",
        owner_scope="household",
        redaction_status="redacted",
    )


def render_sample_output_pack_markdown_v112() -> str:
    manifest = _safe_fixture_manifest_v110()
    portfolio_review = build_portfolio_data_quality_review_v109()
    quarantine_review = review_raw_input_quarantine_manifest_v110(manifest)
    cross_review = build_portfolio_quarantine_cross_review_v111(manifest)
    sections = [
        "# Sample Output Pack（fixture-only / stdout）",
        "",
        _SAMPLE_DISCLAIMER,
        "",
        "---",
        "",
        render_portfolio_data_quality_review_markdown_v109(portfolio_review),
        "",
        "---",
        "",
        render_raw_input_quarantine_review_markdown_v110(manifest, quarantine_review),
        "",
        "---",
        "",
        render_portfolio_quarantine_cross_review_markdown_v111(
            portfolio_review,
            quarantine_review,
            cross_review,
        ),
        "",
        "---",
        "",
        "## Weekly / Monthly Samples",
        "- 週次・月次は `reports-private/sample_outputs/weekly_candidate_brief_sample.md` 等を参照（copy-ready fixture 由来）",
        "- 本 CLI は cache write ではなく、品質/quarantine 系を stdout に連結するのみ",
        "",
    ]
    return "\n".join(sections)
