from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.github_repo_settings_checklist import build_github_repo_settings_checklist


def test_github_repo_settings_checklist_no_secrets(tmp_path: Path) -> None:
    result = build_github_repo_settings_checklist(
        repo="RUotani/invest-alpha-os",
        repo_root=tmp_path,
    )
    assert result.json_payload["secrets_printed"] is False
    assert result.json_payload["settings_mutated"] is False
    assert result.json_payload["manual_check_required_count"] >= 1
