from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_schema_guard import (
    build_manual_data_schema_validation,
    detect_prohibited_headers,
)


def test_detect_prohibited_headers() -> None:
    hits = detect_prohibited_headers(["ticker", "account_id", "close"])
    assert "account_id" in hits


def test_schema_validation_pass(tmp_path: Path) -> None:
    csv_path = tmp_path / "manual_jp_bars.csv"
    csv_path.write_text(
        "ticker,date,open,high,low,close,volume\n"
        "5802,2026-05-27,100,110,90,105,1000\n"
        "285A,2026-05-27,200,210,190,205,500\n",
        encoding="utf-8",
    )
    result = build_manual_data_schema_validation(
        input_path=csv_path,
        targets_csv="5802,285A",
        report_date="2026-05-29",
    )
    assert result.json_payload["schema_valid"] is True
    assert result.json_payload["prohibited_columns_detected"] is False


def test_schema_validation_rejects_prohibited_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "manual_jp_bars.csv"
    csv_path.write_text(
        "ticker,date,close,account\n"
        "5802,2026-05-27,105,secret\n",
        encoding="utf-8",
    )
    result = build_manual_data_schema_validation(
        input_path=csv_path,
        report_date="2026-05-29",
    )
    assert result.json_payload["prohibited_columns_detected"] is True
    assert result.json_payload["schema_valid"] is False
