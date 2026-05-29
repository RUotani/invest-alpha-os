from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_schema_probe import headers_look_like_ohlcv, probe_path_ohlcv_schema


def test_headers_look_like_ohlcv_pass() -> None:
    assert headers_look_like_ohlcv(["ticker", "date", "open", "high", "low", "close", "volume"]) is True


def test_headers_look_like_ohlcv_rejects_account() -> None:
    assert headers_look_like_ohlcv(["ticker", "date", "close", "account_id"]) is False


def test_probe_path_ohlcv_schema(tmp_path: Path) -> None:
    path = tmp_path / "broker_export.csv"
    path.write_text(
        "ticker,date,open,high,low,close,volume\n285A,2026-05-27,1,2,1,1.5,100\n",
        encoding="utf-8",
    )
    ok, reason = probe_path_ohlcv_schema(path)
    assert ok is True
    assert reason == "ohlcv_schema_match"
