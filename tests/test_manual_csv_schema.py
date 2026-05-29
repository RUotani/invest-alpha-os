from __future__ import annotations

from invis_alpha_os.reports.manual_csv_schema import (
    map_csv_headers,
    missing_required_columns,
    normalize_ticker,
    parse_bar_date,
)


def test_map_csv_headers_japanese_aliases() -> None:
    headers = ["銘柄コード", "日付", "始値", "高値", "安値", "終値", "出来高"]
    mapped = map_csv_headers(headers)
    assert missing_required_columns(mapped) == []
    assert mapped["ticker"] == "銘柄コード"


def test_normalize_ticker_strips_suffix() -> None:
    wire, warnings = normalize_ticker("5802.T")
    assert wire == "5802"
    assert "ticker_suffix_stripped" in warnings


def test_normalize_ticker_rejects_invalid() -> None:
    wire, _warnings = normalize_ticker("INVALID!!")
    assert wire is None


def test_parse_bar_date_formats() -> None:
    assert parse_bar_date("2026-05-27") == parse_bar_date("20260527")
    assert parse_bar_date("2026/05/27") == parse_bar_date("2026-05-27")
