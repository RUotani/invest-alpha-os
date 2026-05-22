"""R7.0-Ops-A: autonomous local operator runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.operator.policy import load_operator_runner_policy
from invis_alpha_os.operator.runner import RunnerStop, run_operator_task
from invis_alpha_os.operator.task_spec import load_operator_task

runner = CliRunner()


def test_load_default_policy_and_task() -> None:
    policy = load_operator_runner_policy(CONFIG_DIR / "operator_runner_policy.yaml")
    task = load_operator_task(CONFIG_DIR / "tasks" / "r7_0_discovery_readonly_smoke.yaml")
    assert policy.default_mode == "dry_run"
    assert policy.live_http_gate.env_var == "CONFIRM_LIVE_HTTP"
    assert task.task_id == "r7_0_discovery_readonly_smoke"
    assert len(task.steps) == 3


def test_dry_run_writes_checkpoint_without_executing(tmp_path: Path) -> None:
    state = run_operator_task(
        task_path=CONFIG_DIR / "tasks" / "r7_0_discovery_readonly_smoke.yaml",
        policy_path=CONFIG_DIR / "operator_runner_policy.yaml",
        mode="dry_run",
        outputs_root=tmp_path,
    )
    run_dir = tmp_path / "operator" / "runner" / state.task_id / state.run_id
    checkpoint = json.loads((run_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert state.status == "completed"
    assert checkpoint["mode"] == "dry_run"
    assert len(checkpoint["steps"]) == 3
    assert all(s["status"] == "planned" for s in checkpoint["steps"])
    assert not (run_dir / "discover_jp.json").exists()
    evidence = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
    assert evidence["steps_completed"] == 0


def test_forbidden_cli_flag_stops(tmp_path: Path) -> None:
    bad_task = tmp_path / "bad_task.yaml"
    bad_task.write_text(
        """
task_id: bad_live
version: ops_task.v1
risk_class: readonly
steps:
  - id: live_step
    kind: cli
    command: discover-jp
    args: ["--live"]
    output_artifact: out.json
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(RunnerStop, match="forbidden cli flag"):
        run_operator_task(
            task_path=bad_task,
            policy_path=CONFIG_DIR / "operator_runner_policy.yaml",
            mode="dry_run",
            outputs_root=tmp_path / "out",
        )


def test_merge_discovery_step_execute_readonly(tmp_path: Path) -> None:
    from invis_alpha_os.discovery.cross_market_contract import SCHEMA_VERSION
    from invis_alpha_os.operator.policy import load_operator_runner_policy
    from invis_alpha_os.operator.runner import _run_merge_discovery_step
    from invis_alpha_os.operator.task_spec import load_operator_task

    task_path = tmp_path / "merge_only.yaml"
    task_path.write_text(
        """
task_id: merge_only
version: ops_task.v1
risk_class: readonly
steps:
  - id: merge_cross_market
    kind: merge_discovery_json
    inputs: [jp.json, us.json]
    output_artifact: merged.json
""".strip(),
        encoding="utf-8",
    )
    run_dir = tmp_path / "run_dir"
    run_dir.mkdir()
    jp = {"schema_version": SCHEMA_VERSION, "market": "jp", "common_candidates": [], "summary": {}}
    us = {"schema_version": SCHEMA_VERSION, "market": "us", "common_candidates": [], "summary": {}}
    (run_dir / "jp.json").write_text(json.dumps(jp), encoding="utf-8")
    (run_dir / "us.json").write_text(json.dumps(us), encoding="utf-8")

    task = load_operator_task(task_path)
    policy = load_operator_runner_policy(CONFIG_DIR / "operator_runner_policy.yaml")
    rec = _run_merge_discovery_step(step=task.steps[0], run_dir=run_dir, policy=policy)
    assert rec.status == "completed"
    merged = json.loads((run_dir / "merged.json").read_text(encoding="utf-8"))
    assert merged["schema_version"] == SCHEMA_VERSION
    assert "markets" in merged


def test_cli_operator_runner_dry_run() -> None:
    r = runner.invoke(
        app,
        [
            "operator-runner",
            "run",
            "--task",
            str(CONFIG_DIR / "tasks" / "r7_0_discovery_readonly_smoke.yaml"),
            "--dry-run",
        ],
    )
    assert r.exit_code == 0
    assert "operator-runner: status=completed" in r.stdout
    assert "mode=dry_run" in r.stdout


def test_forbidden_output_in_stdout_stops(tmp_path: Path) -> None:
    from invis_alpha_os.operator.runner import _check_stdout_policy
    from invis_alpha_os.operator.policy import load_operator_runner_policy

    policy = load_operator_runner_policy(CONFIG_DIR / "operator_runner_policy.yaml")
    with pytest.raises(RunnerStop, match="forbidden output term"):
        _check_stdout_policy("please buy now", policy, step_id="x")
# dev-loop smoke marker: 20260522T142443Z (2026-05-22T14:31:25Z)
