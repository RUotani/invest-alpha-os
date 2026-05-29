from __future__ import annotations

from pathlib import Path

from invis_alpha_os.reports.jquants_env_file_discovery import (
    build_jquants_env_file_discovery,
    inspect_env_file_keys,
    merge_env_for_preflight,
)


def test_inspect_env_file_keys_no_values_in_payload(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "JQUANTS_ENABLED=true\nJQUANTS_API_BASE_URL=https://api.example.com\n"
        "JQUANTS_API_KEY=secret-not-printed\n",
        encoding="utf-8",
    )
    info = inspect_env_file_keys(env_path)
    assert "secret" not in str(info)
    assert info["keys"]["JQUANTS_API_KEY"] == "present_nonempty"


def test_merge_env_for_preflight(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("JQUANTS_ENABLED=1\nJQUANTS_API_KEY=abc\nJQUANTS_API_BASE_URL=https://x\n", encoding="utf-8")
    merged = merge_env_for_preflight(env_file=env_path)
    assert merged.get("JQUANTS_ENABLED") == "1"
    assert "abc" not in str(merged.values()) or merged.get("JQUANTS_API_KEY") == "abc"


def test_discovery_finds_candidate(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "JQUANTS_ENABLED=1\nJQUANTS_API_KEY=k\nJQUANTS_API_BASE_URL=https://api.test\n",
        encoding="utf-8",
    )
    result = build_jquants_env_file_discovery(report_date="2026-05-29", repo_root=tmp_path)
    assert result.selected_env_file == env_path
    assert result.json_payload["required_keys_present"] is True
