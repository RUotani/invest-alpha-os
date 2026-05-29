from __future__ import annotations

from pathlib import Path

from invis_alpha_os.data.jquants_daily_bars_cache import save_jquants_daily_bars_cache
from invis_alpha_os.reports.manual_csv_import_plan import build_manual_csv_import_plan

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "sample_5802_bars.csv"


def test_import_plan_detects_rows_newer_than_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    save_jquants_daily_bars_cache(
        "5802",
        [{"date": "2026-03-06", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0}],
        source="jquants",
        fetched_at="2026-03-06T00:00:00Z",
    )
    plan = build_manual_csv_import_plan(
        csv_path=FIXTURE,
        targets_csv="5802",
        report_date="2026-05-27",
    )
    assert plan.json_payload["validated"] is True
    assert plan.json_payload["importable"] is True
    assert plan.json_payload["rows_newer_than_cache_total"] > 0
    assert "importable: true" in plan.markdown_text
    ticker_row = plan.json_payload["per_ticker"][0]
    assert ticker_row["would_improve_stale"] is True


def test_import_plan_not_importable_when_no_new_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    save_jquants_daily_bars_cache(
        "5802",
        [
            {"date": "2026-03-07", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0},
            {"date": "2026-05-27", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0},
        ],
        source="jquants",
        fetched_at="2026-05-27T00:00:00Z",
    )
    plan = build_manual_csv_import_plan(
        csv_path=FIXTURE,
        targets_csv="5802",
        report_date="2026-05-27",
    )
    assert plan.json_payload["importable"] is False
