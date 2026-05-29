from __future__ import annotations

from pathlib import Path

from invis_alpha_os.data.jquants_daily_bars_cache import save_jquants_daily_bars_cache
from invis_alpha_os.reports.manual_csv_import_flow import build_manual_csv_import_flow

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "sample_5802_bars.csv"


def test_import_flow_dry_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    save_jquants_daily_bars_cache(
        "5802",
        [{"date": "2026-03-06", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0}],
        source="jquants",
        fetched_at="2026-03-06T00:00:00Z",
    )
    csv_copy = tmp_path / "manual_jp_bars.csv"
    csv_copy.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    result = build_manual_csv_import_flow(
        csv_path=csv_copy,
        targets_csv="5802",
        report_date="2026-05-27",
        provider="manual_csv",
        scope="JP_ONLY",
        execute_import=False,
        repo_root=tmp_path,
        working_dir=tmp_path / "work",
    )
    assert result.json_payload["overall_status"] == "dry_run_complete"
    assert result.json_payload["actual_import_executed"] is False
    assert result.json_payload["steps"]["validation"]["validated"] is True


def test_import_flow_refused_pii(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("口座番号,date,close\n123,2026-05-27,1\n", encoding="utf-8")
    result = build_manual_csv_import_flow(
        csv_path=bad,
        targets_csv="5802",
        report_date="2026-05-27",
        provider="manual_csv",
        scope="JP_ONLY",
        repo_root=tmp_path,
        working_dir=tmp_path / "work",
    )
    assert result.json_payload["overall_status"] == "pii_guard_failed"
