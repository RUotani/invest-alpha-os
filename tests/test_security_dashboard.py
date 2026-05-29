from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.security_dashboard import build_security_dashboard


def test_security_dashboard_aggregates(tmp_path: Path) -> None:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "tests.yml").write_text("name: t\non: push\n", encoding="utf-8")
    result = build_security_dashboard(
        source_repo_path=tmp_path,
        reports_repo_path=None,
        report_date="2026-05-27",
    )
    assert result.json_payload["secrets_printed"] is False
    assert "overall_grade" in result.json_payload
    assert "leakage_audit" in result.json_payload
