from __future__ import annotations

from pathlib import Path

from invis_alpha_os.data.jquants_daily_bars_cache import save_jquants_daily_bars_cache
from invis_alpha_os.reports.manual_data_import_flow import build_manual_data_import_flow

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "sample_5802_bars.csv"


def test_data_import_flow_dry_run_tsv(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    save_jquants_daily_bars_cache(
        "5802",
        [{"date": "2026-03-06", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0}],
        source="jquants",
        fetched_at="2026-03-06T00:00:00Z",
    )
    tsv = tmp_path / "manual_jp_bars.tsv"
    tsv.write_text(FIXTURE.read_text(encoding="utf-8").replace(",", "\t"), encoding="utf-8")
    result = build_manual_data_import_flow(
        input_path=tsv,
        targets_csv="5802",
        report_date="2026-05-27",
        provider="manual_csv",
        scope="JP_ONLY",
        execute_import=False,
        repo_root=tmp_path,
        working_dir=tmp_path / "work",
    )
    assert result.json_payload["overall_status"] == "dry_run_complete"
    assert result.json_payload["input_type"] == "tsv"
    assert result.json_payload["actual_import_executed"] is False
