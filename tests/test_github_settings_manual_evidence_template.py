from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.github_settings_manual_evidence_template import (
    build_github_settings_manual_evidence_template,
)


def test_manual_evidence_template_structure(tmp_path: Path) -> None:
    result = build_github_settings_manual_evidence_template(
        repo="RUotani/invest-alpha-os",
        repo_root=tmp_path,
        auto_judge=False,
    )
    assert result.json_payload["secrets_printed"] is False
    assert len(result.json_payload["checks"]) >= 5
    assert result.json_payload["checks"][0]["manual_check_status"] == "not_checked"


def test_manual_evidence_template_auto_judge_includes_ruleset_sections(tmp_path) -> None:
    (tmp_path / "SECURITY.md").write_text("# Security\n", encoding="utf-8")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "CODEOWNERS").write_text("* @owner\n", encoding="utf-8")
    result = build_github_settings_manual_evidence_template(
        repo="RUotani/invest-alpha-os",
        repo_root=tmp_path,
        auto_judge=True,
    )
    assert result.json_payload.get("auto_judgement") is True
    assert "branch_protection_evidence" in result.json_payload
    assert "codeql_status_evidence" in result.json_payload
    assert "ruleset_operational_risk" in result.json_payload
