"""R7.0-Ops-C: J-Quants ingest CLI wiring tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.operator.jquants_ingest_wiring import (
    JquantsIngestWiring,
    build_jquants_ingest_cli_argv,
    command_template_for_symbol,
    make_jquants_ingest_executor,
    run_jquants_ingest_subprocess,
)
from invis_alpha_os.operator.policy import load_operator_runner_policy
from invis_alpha_os.operator.runner import run_operator_task
from invis_alpha_os.operator.task_spec import load_operator_task

POLICY = CONFIG_DIR / "operator_runner_policy.yaml"
GATED_TASK = CONFIG_DIR / "tasks" / "r7_0_jquants_ingest_gated_smoke.yaml"

WIRING = JquantsIngestWiring(
    cli_subcommand="jquants-watchlist-bars-cache",
    from_date="2025-06-01",
    to_date="2026-02-17",
)


def test_build_jquants_cli_argv_without_live_flags() -> None:
    argv = build_jquants_ingest_cli_argv(symbol="7011", wiring=WIRING, include_live_flags=False)
    assert "debug" in argv
    assert "jquants-watchlist-bars-cache" in argv
    assert "--codes" in argv and "7011" in argv
    assert "--from-date" in argv and "2025-06-01" in argv
    assert "--to-date" in argv and "2026-02-17" in argv
    assert "--limit" in argv and "1" in argv
    assert "--live" not in argv
    assert "--write-cache" not in argv


def test_build_jquants_cli_argv_with_gated_live_flags() -> None:
    argv = build_jquants_ingest_cli_argv(symbol="7203", wiring=WIRING, include_live_flags=True)
    assert argv.count("--live") == 1
    assert argv.count("--write-cache") == 1


def test_task_yaml_has_ingest_wiring() -> None:
    task = load_operator_task(GATED_TASK)
    assert task.ingest_wiring is not None
    assert task.ingest_wiring.from_date == "2025-06-01"
    assert task.ingest_wiring.cli_subcommand == "jquants-watchlist-bars-cache"


def test_dry_run_writes_planned_commands(tmp_path: Path) -> None:
    state = run_operator_task(
        task_path=GATED_TASK,
        policy_path=POLICY,
        mode="dry_run",
        outputs_root=tmp_path,
    )
    run_dir = tmp_path / "operator" / "runner" / state.task_id / state.run_id
    artifact = json.loads((run_dir / "ingest_batch_results.json").read_text(encoding="utf-8"))
    assert artifact["mode"] == "dry_run"
    assert len(artifact["planned_commands"]) == 3
    cmd = artifact["planned_commands"][0]["dry_run_command"]
    assert "jquants-watchlist-bars-cache" in cmd
    assert "--live" not in cmd
    gated = artifact["planned_commands"][0]["gated_command"]
    assert "--live" in gated and "--write-cache" in gated


def test_execute_gated_simulate_false_uses_mock_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CONFIRM_LIVE_HTTP", "YES")
    monkeypatch.setenv("CONFIRM_CACHE_WRITE", "YES")
    monkeypatch.setenv("CONFIRM_OPERATOR_GATED_INGEST", "YES")

    captured: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout='{"status":"success"}', stderr="")

    task_path = tmp_path / "wired_live.yaml"
    task_path.write_text(
        """
task_id: wired_live
version: ops_task.v2
risk_class: gated_ingest
simulate: false
ingest_wiring:
  cli_subcommand: jquants-watchlist-bars-cache
  from_date: "2025-06-01"
  to_date: "2026-02-17"
steps:
  - id: ingest_one
    kind: gated_ingest_batch
    symbols: ["7011"]
    batch_size: 1
    delay_seconds: 0
    simulate: false
    output_artifact: out.json
""".strip(),
        encoding="utf-8",
    )

    policy = load_operator_runner_policy(POLICY)
    executor = make_jquants_ingest_executor(
        wiring=WIRING,
        repo_root=tmp_path,
        policy=policy,
        simulate=False,
        gates_ok=True,
        subprocess_run=fake_run,
    )
    result = executor("7011")
    assert result.status == "completed"
    assert result.simulated is False
    assert captured
    assert "--live" in captured[0]
    assert "--write-cache" in captured[0]


def test_subprocess_429_maps_to_stop_detail() -> None:
    def fake_429(cmd, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="http_status_429")

    result = run_jquants_ingest_subprocess(
        symbol="7011",
        wiring=WIRING,
        repo_root=Path("/tmp"),
        include_live_flags=True,
        subprocess_run=fake_429,
    )
    assert result.status == "failed"
    assert result.detail == "http_status_429"
