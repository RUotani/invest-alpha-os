"""R7.0-Ops-I7: post-run review and merge helper tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.operator.dev_loop import _load_queue
from invis_alpha_os.operator.post_run_review import (
    build_post_run_review_markdown,
    find_latest_run_id,
    format_post_run_review_markdown,
    load_evidence_summary,
    resolve_productive_run_paths,
)


def _write_evidence(tmp_path: Path, run_id: str, payload: dict) -> Path:
    out = tmp_path / "operator" / "dev_loop" / run_id
    out.mkdir(parents=True, exist_ok=True)
    path = out / "evidence_summary.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log_root = tmp_path / "operator" / "productive_true_longrun_12h" / run_id
    log_root.mkdir(parents=True, exist_ok=True)
    (log_root / "run.log").write_text("productive-longrun-12h SUCCEEDED\n", encoding="utf-8")
    return path


def test_post_run_review_reads_minimal_evidence_fixture(tmp_path: Path) -> None:
    run_id = "20260521T223933Z"
    _write_evidence(
        tmp_path,
        run_id,
        {
            "status": "completed",
            "stop_reason": "min_runtime reached: 720",
            "longrun_exit_success": True,
            "tasks_seen": 32,
            "tasks_executed": 18,
            "prs_created": 18,
            "failed_tasks": [],
            "skipped_tasks": [{"task_id": "t_skip", "reason": "superseded_task", "detail": "x"}],
            "longrun": {
                "longrun_state": "min_runtime_reached",
                "elapsed_minutes": 720.0,
                "min_runtime_minutes": 720,
            },
            "task_results": [
                {
                    "task_id": "t1",
                    "pr_url": "https://github.com/RUotani/invest-alpha-os/pull/115",
                    "ci_wait_status": "success",
                }
            ],
        },
    )
    text = build_post_run_review_markdown(run_id, outputs_root=tmp_path)
    assert "20260521T223933Z" in text
    assert "prs_created: `18`" in text
    assert "skipped_task_count: `1`" in text
    assert "https://github.com/RUotani/invest-alpha-os/pull/115" in text
    assert "min_runtime_reached" in text


def test_post_run_review_does_not_modify_git_state(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    run_id = "20260521T000000Z"
    _write_evidence(tmp_path, run_id, {"status": "completed", "longrun": {}, "task_results": []})

    def fail_git(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("git must not be invoked during post-run review")

    monkeypatch.setattr("subprocess.run", fail_git)
    build_post_run_review_markdown(run_id, outputs_root=tmp_path)


def test_find_latest_run_id(tmp_path: Path) -> None:
    _write_evidence(tmp_path, "20260521T100000Z", {"status": "completed", "task_results": []})
    _write_evidence(tmp_path, "20260521T200000Z", {"status": "completed", "task_results": []})
    assert find_latest_run_id(outputs_root=tmp_path) == "20260521T200000Z"


def test_merge_helper_requires_gate() -> None:
    text = (ROOT_DIR / "scripts/merge_productive_prs_after_review.sh").read_text(encoding="utf-8")
    assert "CONFIRM_PRODUCTIVE_PR_MERGE=YES" in text
    assert "--delete-branch=false" in text
    assert "gh pr merge" in text
    assert "gh pr checks" in text


def test_merge_helper_stops_on_failed_check(tmp_path: Path) -> None:
    script = ROOT_DIR / "scripts/merge_productive_prs_after_review.sh"
    fake_gh = tmp_path / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\nif [[ \"$1\" == \"pr\" && \"$2\" == \"checks\" ]]; then exit 1; fi\nexit 0\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    proc = subprocess.run(
        ["bash", str(script), "--prs", "99"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        env={
            "CONFIRM_PRODUCTIVE_PR_MERGE": "YES",
            "PATH": f"{tmp_path}:/usr/bin:/bin",
        },
    )
    assert proc.returncode != 0
    assert "checks failed" in (proc.stderr or proc.stdout)


def test_review_script_wrapper() -> None:
    text = (ROOT_DIR / "scripts/review_productive_longrun.sh").read_text(encoding="utf-8")
    assert "post-run-review" in text
    assert "operator-runner" in text or "invis_alpha_os.cli.main" in text


def test_v2_queue_exists_and_task_count() -> None:
    path = ROOT_DIR / "config/tasks/autonomous_dev_queue_productive_12h_v2.yaml"
    assert path.is_file()
    tasks = _load_queue(path)
    assert 28 <= len(tasks) <= 36
    text = path.read_text(encoding="utf-8").lower()
    for forbidden in (
        "cache write",
        "gmail send",
        "trading recommendation",
        "target price",
        "gh pr merge",
        "live http",
    ):
        assert forbidden not in text
    ids = {t.task_id for t in tasks}
    for stale in (
        "ops_i_min_max_runtime_tests",
        "ops_i_profile_runtime_warning",
        "ops_i_true_longrun_profile_validation",
        "ops_i_heartbeat_coverage",
    ):
        assert stale not in ids


def test_productive_scripts_not_using_v2_queue_by_default() -> None:
    s8 = (ROOT_DIR / "scripts/run_productive_true_longrun_8h.sh").read_text(encoding="utf-8")
    s12 = (ROOT_DIR / "scripts/run_productive_true_longrun_12h.sh").read_text(encoding="utf-8")
    assert "productive_12h_v2" not in s8
    assert "productive_12h_v2" not in s12
# dev-loop smoke marker: 20260522T130932Z (2026-05-22T13:09:33Z)
