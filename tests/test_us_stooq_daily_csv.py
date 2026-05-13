"""Main R4: Stooq CSV → sanitized bar dicts (strict parser)."""

from __future__ import annotations

import re

import pytest

from invis_alpha_os.data.us_stooq_daily_csv import parse_stooq_daily_csv_to_rows

_VALID = (
    "Date,Open,High,Low,Close,Volume\n"
    "2024-06-03,410.0,412.0,408.0,411.0,900000\n"
    "2024-06-04,411,413,410,412,910000\n"
)


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
