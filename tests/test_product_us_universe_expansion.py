"""Product P6: US 30+ expansion config and read-only gap report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from invis_alpha_os.product.us_universe_expansion import (
    build_us_universe_expansion_report,
    load_us_universe_expansion_config,
)
from invis_alpha_os.signals.momentum import load_bars_json_file

REPO = Path(__file__).resolve().parents[1]
FIX_MSFT = REPO / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json"


def test_expansion_config_loads() -> None:
    cfg = load_us_universe_expansion_config()
    assert cfg["schema_version"] == 1
    symbols = [t["symbol"] for t in cfg["targets"]]
    assert len(symbols) == 36
    assert len(symbols) == len(set(symbols))


def test_duplicate_symbol_fail_closed(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "targets": [
                    {"symbol": "MSFT", "tier": "1", "theme": "t", "reason": "r"},
                    {"symbol": "MSFT", "tier": "1", "theme": "t", "reason": "r2"},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_us_universe_expansion_config(p)


def test_symbol_count_matches_yaml() -> None:
    cfg = load_us_universe_expansion_config()
    assert len(cfg["targets"]) == 36


def test_tier_filter_missing_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.product.us_universe_expansion as exp

    mini_cfg = tmp_path / "mini.yaml"
    mini_cfg.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "targets": [
                    {"symbol": "MSFT", "tier": "1", "theme": "ai", "reason": "t"},
                    {"symbol": "AMD", "tier": "1", "theme": "ai", "reason": "m"},
                    {"symbol": "ZZZZ", "tier": "2", "theme": "ai", "reason": "m2"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(exp, "ROOT_DIR", tmp_path)
    report = build_us_universe_expansion_report(
        path_base=tmp_path, config_path=mini_cfg, tier="1", missing_only=True
    )
    assert report["filter_tier"] == "1"
    assert report["filtered_refresh_order"] == ["AMD", "MSFT"]
    assert report["tier_1_missing_refresh_order"] == ["AMD", "MSFT"]


def test_gap_report_detects_missing_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import invis_alpha_os.product.us_universe_expansion as exp

    mini_cfg = tmp_path / "mini.yaml"
    mini_cfg.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "universe_name": "test",
                "targets": [
                    {"symbol": "MSFT", "tier": "1", "theme": "ai", "reason": "test"},
                    {"symbol": "ZZZZ", "tier": "3", "theme": "ai", "reason": "missing"},
                ],
            }
        ),
        encoding="utf-8",
    )
    outputs = tmp_path / "outputs"
    cache_dir = outputs / "market_data" / "us_daily_bars"
    cache_dir.mkdir(parents=True)
    import invis_alpha_os.data.us_daily_bars_cache as usc

    monkeypatch.setattr(usc, "OUTPUTS_DIR", outputs)
    bars = load_bars_json_file(FIX_MSFT)
    usc.save_us_daily_bars_cache(
        "MSFT",
        [dict(b) for b in bars],
        source="local_fixture",
        fetched_at="2026-05-23T12:00:00+00:00",
    )
    monkeypatch.setattr(exp, "ROOT_DIR", tmp_path)
    report = build_us_universe_expansion_report(path_base=tmp_path, config_path=mini_cfg)
    assert "MSFT" in report["parse_ok_symbols"]
    assert "ZZZZ" in report["missing_symbols"]
    assert report["next_gated_refresh_order"][0] == "ZZZZ"
