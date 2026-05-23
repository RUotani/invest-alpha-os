"""R7.0-Ops-I12-A: operator autopilot status tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from invis_alpha_os.operator.operator_autopilot import (
    collect_autopilot_status,
    collect_git_worktree,
    collect_main_ci,
    collect_open_prs,
    collect_origin_main_sha,
    format_autopilot_status_markdown,
)


def test_collect_open_prs_parses_json() -> None:
    payload = [
        {
            "number": 201,
            "title": "Ops-J",
            "state": "OPEN",
            "isDraft": False,
            "mergeStateStatus": "CLEAN",
            "headRefName": "work/x",
        }
    ]

    def fake_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(cmd, 0, json.dumps(payload), "")

    rows, warnings = collect_open_prs(gh_runner=fake_gh)
    assert not warnings
    assert rows[0].number == 201
    assert rows[0].merge_state_status == "CLEAN"


def test_autopilot_status_markdown_with_mocks(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = "20260523T112747Z"
    ev = tmp_path / "operator" / "dev_loop" / run_id
    ev.mkdir(parents=True)
    (ev / "evidence_summary.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "stop_reason": "early_completion: pr_cap_reached",
                "tasks_seen": 84,
                "tasks_executed": 15,
                "prs_created": 15,
                "task_results": [{"pr_url": "https://github.com/x/pull/185"}],
            }
        ),
        encoding="utf-8",
    )

    def fake_git(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if len(cmd) >= 2 and cmd[1] == "fetch":
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if len(cmd) >= 2 and cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, 0, "abc123def\n", "")
        if len(cmd) >= 2 and cmd[1] == "branch":
            return subprocess.CompletedProcess(cmd, 0, "main\n", "")
        if len(cmd) >= 2 and cmd[1] == "status":
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def fake_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if cmd[1:3] == ["pr", "list"]:
            return subprocess.CompletedProcess(cmd, 0, "[]", "")
        if cmd[1:3] == ["run", "list"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                json.dumps(
                    [
                        {
                            "databaseId": "1",
                            "workflowName": "tests",
                            "status": "completed",
                            "conclusion": "success",
                            "headBranch": "main",
                            "updatedAt": "2026-05-23T12:00:00Z",
                        }
                    ]
                ),
                "",
            )
        return subprocess.CompletedProcess(cmd, 0, "[]", "")

    result = collect_autopilot_status(
        run_id=run_id,
        repo_root=tmp_path,
        outputs_root=tmp_path,
        fetch_main=True,
        git_runner=fake_git,
        gh_runner=fake_gh,
    )
    text = format_autopilot_status_markdown(result)
    assert "abc123def" in text
    assert run_id in text
    assert "early_completion" in text
    assert "post-run-review" in text
    assert "post-run-integrate" in text
    assert result.main_ci_ok is True


def test_autopilot_does_not_invoke_merge_commands(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls: list[list[str]] = []

    def record_git(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        if len(cmd) >= 2 and cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, 0, "deadbeef\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def record_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "[]", "")

    collect_autopilot_status(
        repo_root=tmp_path,
        outputs_root=tmp_path,
        fetch_main=False,
        git_runner=record_git,
        gh_runner=record_gh,
    )
    joined = " ".join(" ".join(c) for c in calls).lower()
    assert "gh pr merge" not in joined
    assert "git push" not in joined
    assert "gh pr close" not in joined


def test_collect_open_prs_gh_failure_warns() -> None:
    def fail_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(cmd, 1, "", "rate limit")

    rows, warnings = collect_open_prs(gh_runner=fail_gh)
    assert rows == []
    assert any("gh pr list failed" in w for w in warnings)


def test_collect_main_ci_no_runs_warns() -> None:
    def empty_gh(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(cmd, 0, "[]", "")

    summary, warnings = collect_main_ci(gh_runner=empty_gh)
    assert summary is None
    assert any("no workflow runs" in w for w in warnings)


def test_git_status_redacts_secret_like_paths(tmp_path: Path) -> None:
    def fake_git(cmd, **kwargs):  # type: ignore[no-untyped-def]
        if len(cmd) >= 2 and cmd[1] == "branch":
            return subprocess.CompletedProcess(cmd, 0, "main\n", "")
        if len(cmd) >= 2 and cmd[1] == "status":
            return subprocess.CompletedProcess(cmd, 0, " M .env\n M README.md\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    branch, clean, dirty_count, warnings = collect_git_worktree(
        repo_root=tmp_path, git_runner=fake_git
    )
    assert branch == "main"
    assert clean is False
    assert dirty_count == 1
    assert any("redacted" in w for w in warnings)


def test_collect_origin_main_skips_fetch_when_disabled(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def record_git(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "sha123\n", "")

    sha, warnings = collect_origin_main_sha(
        repo_root=tmp_path, git_runner=record_git, fetch=False
    )
    assert sha == "sha123"
    assert not warnings
    assert not any(len(c) >= 2 and c[1] == "fetch" for c in calls)
