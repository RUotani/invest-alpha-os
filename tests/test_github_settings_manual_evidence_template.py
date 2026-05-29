from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.github_settings_manual_evidence_template import (
    build_github_settings_manual_evidence_template,
)


def test_manual_evidence_template_structure(tmp_path: Path) -> None:
    result = build_github_settings_manual_evidence_template(
        repo="RUotani/invest-alpha-os",
        repo_root=tmp_path,
    )
    assert result.json_payload["secrets_printed"] is False
    assert len(result.json_payload["checks"]) >= 5
    assert result.json_payload["checks"][0]["manual_check_status"] == "not_checked"
