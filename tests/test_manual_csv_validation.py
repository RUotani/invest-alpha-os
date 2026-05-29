from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_csv_validation import validate_manual_csv_file

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "sample_5802_bars.csv"


def test_validate_manual_csv_fixture_ok() -> None:
    result = validate_manual_csv_file(
        csv_path=FIXTURE,
        targets_csv="5802",
        report_date="2026-05-27",
    )
    assert result.json_payload["validated"] is True
    assert result.json_payload["row_count"] == 3
    assert result.json_payload["date_max"] == "2026-05-27"
    assert "5802" in result.rows_by_ticker


def test_validate_manual_csv_rejects_out_of_scope_target() -> None:
    result = validate_manual_csv_file(
        csv_path=FIXTURE,
        targets_csv="6645",
        report_date="2026-05-27",
    )
    assert result.json_payload["validated"] is False
    assert any("target_out_of_scope" in e for e in result.json_payload["errors"])


def test_validate_manual_csv_rejects_future_date(tmp_path: Path) -> None:
    bad = tmp_path / "future.csv"
    bad.write_text(
        "ticker,date,open,high,low,close,volume\n5802,2099-01-01,1,2,1,1.5,100\n",
        encoding="utf-8",
    )
    result = validate_manual_csv_file(
        csv_path=bad,
        targets_csv="5802",
        report_date="2026-05-27",
    )
    assert result.json_payload["validated"] is False
    assert any("future_date" in e for e in result.json_payload["errors"])
