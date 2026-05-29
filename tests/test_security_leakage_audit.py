from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.security_leakage_audit import build_security_leakage_audit


def test_security_leakage_audit_redacted(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("no secrets here", encoding="utf-8")
    result = build_security_leakage_audit(source_repo_path=tmp_path, reports_repo_path=None)
    assert result.json_payload["secrets_printed"] is False
    assert "overall_status" in result.json_payload
    assert "source_repo" in result.json_payload
