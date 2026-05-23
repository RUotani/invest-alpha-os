"""R7.0-Ops-I12-A: operator autopilot status tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from invis_alpha_os.operator.operator_autopilot import (
    collect_autopilot_status,
    collect_open_prs,
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
