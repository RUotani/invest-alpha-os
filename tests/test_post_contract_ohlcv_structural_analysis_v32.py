from __future__ import annotations

import json
from pathlib import Path

from invis_alpha_os.reports.post_contract_ohlcv_structural_analysis_v32 import (
    build_post_contract_structural_v32,
    build_structural_theme_deep_dive,
)


def test_build_structural_theme_deep_dive_from_fixture(tmp_path: Path) -> None:
    latest = tmp_path / "latest"
    latest.mkdir()
    context = {
        "candidates": [
            {
                "ticker": "285A",
                "name": "285A test",
                "classification": "top_pick",
                "timing": "wait_for_pullback",
                "theme": "memory,semiconductors,ai_infra",
                "latest_bar_date": "2026-03-06",
                "returns": {"d5": -0.05, "d20": -0.04, "d60": 1.2},
                "moving_averages": {
                    "dist_ma25_pct": -0.03,
                    "dist_ma75_pct": 0.36,
                    "dist_ma200_pct": 1.5,
                },
                "range_52w": {"dist_high_pct": -0.18},
                "volume": {"ratio20": 0.95},
                "freshness": "要更新",
            },
            {
                "ticker": "5802",
                "name": "5802 test",
                "classification": "top_pick",
                "timing": "overheated_watch",
                "theme": "energy,automotive_wire",
                "latest_bar_date": "2026-03-06",
                "returns": {"d5": -0.04, "d20": 0.26, "d60": 0.47},
                "moving_averages": {
                    "dist_ma25_pct": 0.11,
                    "dist_ma75_pct": 0.35,
                    "dist_ma200_pct": 0.93,
                },
                "range_52w": {"dist_high_pct": -0.14},
                "volume": {"ratio20": 0.99},
                "freshness": "要更新",
            },
        ]
    }
    (latest / "chatgpt_invest_context_pack.json").write_text(
        json.dumps(context), encoding="utf-8"
    )
    md, payload = build_structural_theme_deep_dive(
        report_date="2026-05-29",
        reports_latest_dir=latest,
        focus_csv="285A,5802",
    )
    assert "285A" in md
    tickers = {r["ticker"]: r for r in payload["per_ticker"]}
    assert tickers["285A"]["watch_priority"] in {"watch_high", "watch_medium"}
    assert "secret" not in md.lower()
    assert payload["secrets_printed"] is False


def test_build_v32_no_post_contract_discovery(tmp_path: Path, monkeypatch) -> None:
    latest = tmp_path / "latest"
    latest.mkdir()
    (latest / "chatgpt_invest_context_pack.json").write_text(
        json.dumps({"candidates": []}),
        encoding="utf-8",
    )

    def _fake_discover(**_kwargs: object) -> list[dict[str, object]]:
        return []

    monkeypatch.setattr(
        "invis_alpha_os.reports.post_contract_ohlcv_structural_analysis_v32.discover_manual_data_candidates",
        lambda **_: _fake_discover(),
    )
    result = build_post_contract_structural_v32(
        report_date="2026-05-29",
        repo_root=tmp_path,
        reports_latest_dir=latest,
        targets_csv="285A",
    )
    assert result.discovery_json["post_contract_ohlcv_found"] is False
    assert "yahoo" in result.quick_guide_json["recommended_source"]
