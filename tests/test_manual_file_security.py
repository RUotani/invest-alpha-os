from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.manual_file_security import (
    MAX_FILE_BYTES,
    scan_manual_file_security,
)


def test_manual_file_security_passes_clean_csv(tmp_path: Path) -> None:
    path = tmp_path / "manual_jp_bars.csv"
    path.write_text(
        "ticker,date,open,high,low,close,volume\n5802,2026-05-27,1,2,1,2,100\n",
        encoding="utf-8",
    )
    result = scan_manual_file_security(path)
    assert result.status == "passed"
    assert result.json_payload["contents_printed"] is False


def test_manual_file_security_rejects_formula_injection(tmp_path: Path) -> None:
    path = tmp_path / "evil.csv"
    path.write_text("ticker,note\n5802,=cmd|'/c calc'!A0\n", encoding="utf-8")
    result = scan_manual_file_security(path)
    assert result.status == "rejected"
    assert any("formula_injection" in issue for issue in result.issues)


def test_manual_file_security_rejects_oversize(tmp_path: Path) -> None:
    path = tmp_path / "big.csv"
    path.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
    result = scan_manual_file_security(path)
    assert result.status == "rejected"
    assert "file_too_large" in result.issues
