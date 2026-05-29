from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.security.security_leakage_audit import build_security_leakage_audit


def test_security_leakage_audit_redacted(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("no secrets here", encoding="utf-8")
    result = build_security_leakage_audit(source_repo_path=tmp_path, reports_repo_path=None)
    assert result.json_payload["secrets_printed"] is False
    assert "overall_status" in result.json_payload
    assert "source_repo" in result.json_payload


def test_security_leakage_audit_suppresses_docs_placeholder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.security.security_leakage_audit._git_tracked_files",
        lambda _root: ["docs/example.md", ".env.example"],
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "example.md").write_text("JQUANTS_API_KEY=your_api_key_here\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("GMAIL_TOKEN=placeholder\n", encoding="utf-8")
    result = build_security_leakage_audit(source_repo_path=tmp_path, reports_repo_path=None)
    source = result.json_payload["source_repo"]
    assert source["suppressed_false_positive_count"] >= 1
    assert len(source["suspected_secret_hits"]) == 0
