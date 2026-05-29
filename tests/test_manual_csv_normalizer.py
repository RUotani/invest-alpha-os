from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_csv_normalizer import (
    BROKER_FORMAT_AUTO,
    BROKER_FORMAT_GENERIC,
    BROKER_FORMAT_MOOMOO,
    build_manual_csv_normalization,
    detect_broker_format,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "sample_5802_bars.csv"
MOOMOO = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "moomoo_sample.csv"


def test_detect_moomoo_format() -> None:
    assert detect_broker_format(["Symbol", "Time", "Open", "High", "Low", "Close", "Volume"]) == BROKER_FORMAT_MOOMOO


def test_normalize_generic_fixture(tmp_path: Path) -> None:
    result = build_manual_csv_normalization(
        csv_path=FIXTURE,
        report_date="2026-05-27",
        broker_format=BROKER_FORMAT_GENERIC,
        output_path=tmp_path / "normalized.csv",
    )
    assert result.json_payload["ready_for_validation"] is True
    assert result.normalized_path is not None
    assert result.normalized_path.read_text(encoding="utf-8").startswith("ticker,date")


def test_normalize_moomoo_fixture(tmp_path: Path) -> None:
    result = build_manual_csv_normalization(
        csv_path=MOOMOO,
        report_date="2026-05-27",
        broker_format=BROKER_FORMAT_MOOMOO,
        output_path=tmp_path / "moomoo_normalized.csv",
    )
    assert result.json_payload["ready_for_validation"] is True
    text = result.normalized_path.read_text(encoding="utf-8") if result.normalized_path else ""
    assert "285A" in text


def test_auto_detect_without_convert_when_unknown(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("foo,bar\n1,2\n", encoding="utf-8")
    result = build_manual_csv_normalization(
        csv_path=bad,
        report_date="2026-05-27",
        broker_format=BROKER_FORMAT_AUTO,
        output_path=tmp_path / "out.csv",
    )
    assert result.json_payload["ready_for_validation"] is False
