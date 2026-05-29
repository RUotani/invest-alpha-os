from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.github_settings_evidence_pack import build_github_settings_evidence_pack


def test_github_settings_evidence_pack_structure(tmp_path: Path) -> None:
    result = build_github_settings_evidence_pack(
        repo="RUotani/invest-alpha-os",
        repo_root=tmp_path,
    )
    assert result.json_payload["secrets_printed"] is False
    assert result.json_payload["settings_mutated"] is False
    assert "manual_ui_steps" in result.json_payload
    assert "checklist" in result.json_payload
