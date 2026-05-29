from __future__ import annotations

from pathlib import Path

from invis_alpha_os.security.github_actions_security_audit import build_github_actions_security_audit


def test_github_actions_audit_finds_workflow(tmp_path: Path) -> None:
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "tests.yml").write_text(
        "name: tests\non: pull_request\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
        encoding="utf-8",
    )
    result = build_github_actions_security_audit(repo_path=tmp_path)
    assert result.json_payload["workflow_count"] == 1
    assert result.json_payload["secrets_printed"] is False
