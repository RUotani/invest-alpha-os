from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_data_normalizer import (
    build_manual_data_normalization,
    detect_input_type,
)

FIXTURE_CSV = Path(__file__).resolve().parent / "fixtures" / "manual_csv" / "sample_5802_bars.csv"


def test_detect_input_type_tsv(tmp_path: Path) -> None:
    path = tmp_path / "manual_jp_bars.tsv"
    path.write_text("ticker\tdate\n", encoding="utf-8")
    assert detect_input_type(path) == "tsv"


def test_normalize_tsv_to_canonical_csv(tmp_path: Path, monkeypatch) -> None:
    tsv = tmp_path / "manual.tsv"
    tsv.write_text(
        "ticker,date,open,high,low,close,volume\n"
        "5802,2026-05-27,100,110,90,105,1000\n".replace(",", "\t"),
        encoding="utf-8",
    )
    result = build_manual_data_normalization(
        input_path=tsv,
        report_date="2026-05-27",
        output_path=tmp_path / "out.csv",
    )
    assert result.json_payload["input_type"] == "tsv"
    assert result.json_payload["ready_for_validation"] is True
    assert result.normalized_path is not None


def test_xlsx_reports_unsupported_without_openpyxl(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.reports.manual_data_normalizer._openpyxl_available",
        lambda: False,
    )
    xlsx = tmp_path / "manual.xlsx"
    xlsx.write_bytes(b"not-a-real-xlsx")
    result = build_manual_data_normalization(input_path=xlsx, report_date="2026-05-27")
    assert result.json_payload["xlsx_supported"] is False
    assert result.json_payload["ready_for_validation"] is False
