from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_csv_pii_guard import run_manual_csv_pii_guard, scan_csv_headers_for_pii


def test_pii_guard_passes_ohlcv_headers() -> None:
    result = scan_csv_headers_for_pii(
        ["ticker", "date", "open", "high", "low", "close", "volume"],
    )
    assert result.status == "passed"
    assert result.account_data_detected is False


def test_pii_guard_rejects_account_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("ticker,date,口座番号,close\n5802,2026-05-27,123,100\n", encoding="utf-8")
    result = run_manual_csv_pii_guard(csv_path)
    assert result.status == "rejected"
    assert result.account_data_detected is True
