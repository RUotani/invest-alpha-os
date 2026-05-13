"""Main R4: Stooq CSV → sanitized bar dicts (strict parser)."""

from __future__ import annotations

import json
import re

import pytest

from invis_alpha_os.data.us_stooq_daily_csv import (
    classify_stooq_csv_text_safely,
    parse_stooq_daily_csv_to_rows,
)

_VALID = (
    "Date,Open,High,Low,Close,Volume\n"
    "2024-06-03,410.0,412.0,408.0,411.0,900000\n"
    "2024-06-04,411,413,410,412,910000\n"
)


def test_classify_valid_csv_metadata() -> None:
    diag = classify_stooq_csv_text_safely(_VALID)
    assert diag["body_kind"] == "csv_like"
    assert diag["delimiter_guess"] == "comma"
    assert diag["has_required_columns"] is True
    assert diag["required_columns_missing"] == []
    assert len(diag["header_columns_sanitized"]) <= 12


def test_classify_no_data_hint() -> None:
    diag = classify_stooq_csv_text_safely("No data available for ticker.\n")
    assert diag["body_kind"] == "no_data_like"
    assert diag["has_required_columns"] is False


def test_classify_html_hint() -> None:
    diag = classify_stooq_csv_text_safely("<html><body>blocked</body></html>\n")
    assert diag["body_kind"] == "html_like"


def test_classify_api_key_required_overrides_plain_prose() -> None:
    diag = classify_stooq_csv_text_safely(
        "Get your apikey? See https://stooq.com/ for CSV.\nThere is no table here.",
    )
    assert diag["body_kind"] == "api_key_required"


def test_classify_api_key_hint_in_bounded_sample() -> None:
    diag = classify_stooq_csv_text_safely(
        "This feed now requires api key authentication for bulk access.\n"
    )
    assert diag["body_kind"] == "api_key_required"


def test_classify_semicolon_delimiter() -> None:
    body = "Date;Open;High;Low;Close;Volume\n2024-01-02;1;2;3;4;5\n"
    diag = classify_stooq_csv_text_safely(body)
    assert diag["delimiter_guess"] == "semicolon"


def test_classify_empty_body_explicit() -> None:
    diag = classify_stooq_csv_text_safely("")
    assert diag["body_kind"] == "empty"
    assert diag["line_count_limited"] == 0


def test_classify_whitespace_only_same_as_empty() -> None:
    diag = classify_stooq_csv_text_safely("  \n\t  \r\n")
    assert diag["body_kind"] == "empty"


def test_classify_api_key_overrides_html_shell() -> None:
    diag = classify_stooq_csv_text_safely(
        "<html><body>You need apikey for CSV download</body></html>\n",
    )
    assert diag["body_kind"] == "api_key_required"


def test_classify_api_key_from_sanitized_header_cell_without_raw_banner() -> None:
    diag = classify_stooq_csv_text_safely("Get your apikey?,Open,Px\nMsft\n")
    assert diag["body_kind"] == "api_key_required"


def test_classify_unclosed_quote_header_no_body_leak_diagnostic() -> None:
    leaky = '"Date,Oops unclosed quoted field\nMore secret noise here\n'
    diag = classify_stooq_csv_text_safely(leaky)
    blob = json.dumps(diag)
    assert "secret" not in blob.lower()


def test_classify_delimiter_drift_heuristic_vs_comma_header() -> None:
    body = (
        "Date,Open,High,Low,Close,Volume\n"
        "2024-01-02\t1\t2\t3\t4\t5\n"
        "2024-01-03\t1\t2\t3\t4\t5\n"
    )
    diag = classify_stooq_csv_text_safely(body)
    assert diag["body_kind"] == "delimiter_drift"
    assert diag["delimiter_guess"] == "comma"


def test_classify_truncates_header_cells_without_raw_leaks() -> None:
    long_cell = ("X" * 80) + "secret_part"
    line = ",".join(
        ["Date", "Open", long_cell, "Low", "Close", "Volume"],
    )
    diag = classify_stooq_csv_text_safely(line + "\n1,2,3,4,5")
    assert all(len(c) <= 40 for c in diag["header_columns_sanitized"])
    assert "secret" not in json.dumps(diag)


def test_classify_headerless_numeric_row_omits_header_tokens() -> None:
    body = "2024-01-02,100.0,110.0,90.0,105.0,1234567\n"
    diag = classify_stooq_csv_text_safely(body)
    assert diag["header_columns_sanitized"] == []
    assert diag["has_required_columns"] is False
    blob = json.dumps(diag, ensure_ascii=False)
    assert "2024" not in blob
    assert "100.0" not in blob
    assert "1234567" not in blob


def test_classify_sanitizes_non_alnum_header_cells() -> None:
    diag = classify_stooq_csv_text_safely("Da@te,Open#,High$,Low!,Close:,Volume@\n")
    assert "?" in diag["header_columns_sanitized"][0]


def test_parse_valid_csv_returns_sanitized_rows() -> None:
    rows = parse_stooq_daily_csv_to_rows(_VALID)
    assert len(rows) == 2
    assert rows[0]["date"] == "2024-06-03"
    assert rows[0]["open"] == 410.0
    assert rows[0]["volume"] == 900000.0
    assert rows[1]["close"] == 412.0
    assert set(rows[0]) == {"date", "open", "high", "low", "close", "volume"}


@pytest.mark.parametrize(
    "csv_text,expected_code",
    (
        ("Ticker,Open\n1,2\n", "stooq_csv_missing_required_columns"),
        ("", "stooq_csv_no_rows"),
        ("   \n\t  \n", "stooq_csv_no_rows"),
    ),
)
def test_parse_rejects_schema_or_empty(csv_text: str, expected_code: str) -> None:
    with pytest.raises(ValueError, match=f"^{re.escape(expected_code)}$"):
        parse_stooq_daily_csv_to_rows(csv_text)


def test_parse_invalid_numeric_opaque_error() -> None:
    csv_bad = (
        "Date,Open,High,Low,Close,Volume\n"
        "2024-06-03,NOT_A_NUMBER,412,408,411,900000\n"
    )
    with pytest.raises(ValueError) as ei:
        parse_stooq_daily_csv_to_rows(csv_bad)
    assert str(ei.value) == "stooq_csv_parse_failed"
    msg = str(ei.value)
    assert "NOT" not in msg
    assert "410" not in msg


def test_exception_messages_never_echo_raw_cells() -> None:
    leaky = (
        "Date,Open,High,Low,Close,Volume\n"
        "2024-06-03,secret_token_xyz,412,408,411,900000\n"
    )
    with pytest.raises(ValueError) as ei:
        parse_stooq_daily_csv_to_rows(leaky)
    assert "secret" not in str(ei.value).lower()


def test_duplicate_dates_rejected() -> None:
    dup = (
        "Date,Open,High,Low,Close,Volume\n"
        "2024-06-03,1,2,3,4,5\n"
        "2024-06-03,1,2,3,4,6\n"
    )
    with pytest.raises(ValueError, match="^stooq_csv_parse_failed$"):
        parse_stooq_daily_csv_to_rows(dup)


def test_zero_open_rejected() -> None:
    bad = (
        "Date,Open,High,Low,Close,Volume\n"
        "2024-06-03,0,1,2,3,4\n"
    )
    with pytest.raises(ValueError, match="^stooq_csv_parse_failed$"):
        parse_stooq_daily_csv_to_rows(bad)
