from __future__ import annotations

from pathlib import Path

from invis_alpha_os.data.jquants_daily_bars_cache import load_jquants_daily_bars_cache, save_jquants_daily_bars_cache
from invis_alpha_os.reports.manual_csv_import_execute import build_manual_csv_import_execute

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "sample_5802_bars.csv"


def _gate_env(targets: str = "5802") -> dict[str, str]:
    return {
        "ALLOW_CACHE_WRITE": "1",
        "CONFIRM_CACHE_WRITE": "YES",
        "CONFIRM_MANUAL_CSV_IMPORT": "YES",
        "CONFIRM_PROVIDER": "manual_csv",
        "CONFIRM_SCOPE": "JP_ONLY",
        "CONFIRM_TARGETS": targets,
    }


def test_execute_dry_run_no_cache_write(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    save_jquants_daily_bars_cache(
        "5802",
        [{"date": "2026-03-06", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0}],
        source="jquants",
        fetched_at="2026-03-06T00:00:00Z",
    )
    result = build_manual_csv_import_execute(
        csv_path=FIXTURE,
        targets_csv="5802",
        report_date="2026-05-27",
        execute_import=False,
        env={},
    )
    assert result.json_payload["dry_run_only"] is True
    assert result.json_payload["cache_write_executed"] is False
    assert result.json_payload["importable"] is True


def test_execute_import_writes_new_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    save_jquants_daily_bars_cache(
        "5802",
        [{"date": "2026-03-06", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0, "volume": 100.0}],
        source="jquants",
        fetched_at="2026-03-06T00:00:00Z",
    )
    result = build_manual_csv_import_execute(
        csv_path=FIXTURE,
        targets_csv="5802",
        report_date="2026-05-27",
        execute_import=True,
        env=_gate_env("5802"),
    )
    assert result.json_payload["overall_status"] == "success"
    assert result.json_payload["cache_write_executed"] is True
    loaded = load_jquants_daily_bars_cache("5802")
    assert loaded is not None
    bars, meta = loaded
    assert meta.get("source") == "manual_csv"
    assert str(bars[-1]["date"]) == "2026-05-27"


def test_execute_refused_without_gates(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("invis_alpha_os.data.jquants_daily_bars_cache.OUTPUTS_DIR", tmp_path)
    result = build_manual_csv_import_execute(
        csv_path=FIXTURE,
        targets_csv="5802",
        report_date="2026-05-27",
        execute_import=True,
        env={},
    )
    assert result.json_payload["overall_status"] == "gate_refused"
