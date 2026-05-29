from __future__ import annotations

import json
from pathlib import Path

from invis_alpha_os.reports.investment_readiness_after_jquants_refresh import (
    build_investment_readiness_v31,
)


def test_build_investment_readiness_v31_from_fixture(tmp_path: Path) -> None:
    latest = tmp_path / "latest"
    latest.mkdir()
    context = {
        "candidates": [
            {
                "ticker": "285A",
                "classification": "top_pick",
                "timing": "wait_for_pullback",
                "latest_bar_date": "2026-03-06",
                "timing_label_ja": "押し目待ち",
            }
        ],
        "summary": {"skip_candidates": ["5801"]},
    }
    (latest / "chatgpt_invest_context_pack.json").write_text(
        json.dumps(context), encoding="utf-8"
    )
    (latest / "cache_refresh_readiness.json").write_text("{}", encoding="utf-8")
    (latest / "trap_analysis.json").write_text(
        json.dumps({"trap_analysis": [{"ticker": "285A", "upside_thesis": ["x"], "downside_thesis": ["y"], "invalidation_conditions": ["z"]}]}),
        encoding="utf-8",
    )
    (latest / "jquants_refresh_freshness_verification.json").write_text(
        json.dumps(
            {
                "refresh_executed": True,
                "per_ticker": [{"ticker": "285A", "after_latest": "2026-03-06", "status": "freshness_improved"}],
            }
        ),
        encoding="utf-8",
    )
    (latest / "manual_data_import_flow.json").write_text(
        json.dumps({"rows_newer_than_cache_total": 0}), encoding="utf-8"
    )
    result = build_investment_readiness_v31(
        report_date="2026-05-29",
        reports_latest_dir=latest,
        targets_csv="285A,5801",
    )
    assert result.readiness_json["manual_import_recommended"] is False
    assert result.readiness_json["context_pack_reflects_v30r_refresh"] is True
    tickers = {r["ticker"]: r for r in result.classification_json["per_ticker"]}
    assert tickers["285A"]["classification"] == "押し目待ち"
    assert tickers["5801"]["classification"] == "見送り"
    assert "secret" not in result.readiness_markdown.lower()
