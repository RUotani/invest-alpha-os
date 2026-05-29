from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.stooq_manual_csv_ingest import (
    combine_stooq_files_to_manual_jp_bars,
    discover_stooq_csv_candidates,
)
from invis_alpha_os.reports.stooq_manual_csv_ticker_inference import infer_ticker_from_filename


def test_infer_ticker_from_filename() -> None:
    assert infer_ticker_from_filename(Path("5802.csv")).ticker == "5802"
    assert infer_ticker_from_filename(Path("285a.csv")).ticker == "285A"
    assert infer_ticker_from_filename(Path("5802.jp.csv")).ticker == "5802"


def test_combine_stooq_files(tmp_path: Path) -> None:
    csv_text = (
        "Date,Open,High,Low,Close,Volume\n"
        "2026-03-07,100,101,99,100,1000\n"
        "2026-05-28,101,102,100,101,1100\n"
    )
    p = tmp_path / "5802.csv"
    p.write_text(csv_text, encoding="utf-8")
    out = tmp_path / "manual_jp_bars.csv"
    meta = combine_stooq_files_to_manual_jp_bars(
        file_ticker_pairs=[(p, "5802")],
        output_path=out,
    )
    assert meta["combined_row_count"] == 2
    assert meta["post_contract_row_count"] == 2
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert "5802" in body
    assert "secret" not in body.lower()


def test_discover_excludes_manual_jp_bars(tmp_path: Path) -> None:
    (tmp_path / "manual_jp_bars.csv").write_text("ticker,date\n", encoding="utf-8")
    (tmp_path / "6645.csv").write_text(
        "Date,Open,High,Low,Close,Volume\n2026-05-28,1,2,1,1,10\n",
        encoding="utf-8",
    )
    found = discover_stooq_csv_candidates(search_dirs=[tmp_path])
    names = {r["filename"] for r in found}
    assert "manual_jp_bars.csv" not in names
    assert "6645.csv" in names
