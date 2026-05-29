from __future__ import annotations

from pathlib import Path

import pytest

from invis_alpha_os.security.leakage_retained_hit_triage import build_leakage_retained_hit_triage


def test_triage_redacted_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "invis_alpha_os.security.leakage_retained_hit_triage._git_tracked_files",
        lambda _root: ["docs/example.md"],
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "example.md").write_text("JQUANTS_API_KEY=your_key\n", encoding="utf-8")
    result = build_leakage_retained_hit_triage(source_repo_path=tmp_path, reports_repo_path=None)
    assert result.json_payload["secrets_printed"] is False
    assert "retained_hit_count" in result.json_payload
    assert "classification_counts" in result.json_payload
