from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from invis_alpha_os.config.env_file_loader import (
    EnvFileLoaderError,
    apply_allowlisted_env_file,
    parse_allowlisted_env_file,
)


def test_parse_allowlisted_env_file_supports_comments_quotes_and_export() -> None:
    text = """
# comment
JQUANTS_ENABLED=true
export JQUANTS_API_BASE_URL="https://example.test/v2"
JQUANTS_API_KEY='secret-not-printed'
OTHER_SECRET=ignored
JQUANTS_ALLOW_LIVE_HTTP=1 # inline comment
"""
    parsed = parse_allowlisted_env_file(text)
    assert parsed["JQUANTS_ENABLED"] == "true"
    assert parsed["JQUANTS_API_BASE_URL"] == "https://example.test/v2"
    assert parsed["JQUANTS_API_KEY"] == "secret-not-printed"
    assert parsed["JQUANTS_ALLOW_LIVE_HTTP"] == "1"
    assert "OTHER_SECRET" not in parsed


def test_apply_allowlisted_env_file_sets_only_missing_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "local.env"
    env_file.write_text(
        "\n".join(
            [
                "JQUANTS_ENABLED=true",
                "JQUANTS_API_BASE_URL=https://example.test/v2",
                "JQUANTS_API_KEY=from-file",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("JQUANTS_ENABLED", raising=False)
    monkeypatch.delenv("JQUANTS_API_BASE_URL", raising=False)
    monkeypatch.delenv("JQUANTS_API_KEY", raising=False)
    monkeypatch.setenv("JQUANTS_ENABLED", "already-set")

    result = apply_allowlisted_env_file(env_file, repo_root=tmp_path)
    assert os.environ["JQUANTS_ENABLED"] == "already-set"
    assert os.environ["JQUANTS_API_BASE_URL"] == "https://example.test/v2"
    assert os.environ["JQUANTS_API_KEY"] == "from-file"
    assert result.keys_loaded == ("JQUANTS_API_BASE_URL", "JQUANTS_API_KEY")
    assert result.keys_skipped_existing == ("JQUANTS_ENABLED",)


def test_apply_allowlisted_env_file_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(EnvFileLoaderError, match="env file not found"):
        apply_allowlisted_env_file(tmp_path / "missing.env", repo_root=tmp_path)


def test_apply_allowlisted_env_file_rejects_git_tracked_file(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    tracked = repo_root / "tracked.env"
    tracked.write_text("JQUANTS_ENABLED=true\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.env"], cwd=repo_root, check=True, capture_output=True)

    with pytest.raises(EnvFileLoaderError, match="refusing git-tracked env file"):
        apply_allowlisted_env_file(tracked, repo_root=repo_root)


def test_apply_allowlisted_env_file_does_not_echo_secret_values(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    env_file = tmp_path / "local.env"
    env_file.write_text("JQUANTS_API_KEY=super-secret-value\n", encoding="utf-8")
    apply_allowlisted_env_file(env_file, repo_root=tmp_path)
    captured = capsys.readouterr()
    assert "super-secret-value" not in captured.out
    assert "super-secret-value" not in captured.err
