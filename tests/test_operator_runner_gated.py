"""R7.0-Ops-B: gated ingest operator runner tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.config.paths import CONFIG_DIR
from invis_alpha_os.operator.gated_ingest import SymbolBatchResult, load_ingest_progress
from invis_alpha_os.operator.policy import load_operator_runner_policy
from invis_alpha_os.operator.runner import RunnerStop, run_operator_task
from invis_alpha_os.operator.task_spec import load_operator_task

GATED_TASK = CONFIG_DIR / "tasks" / "r7_0_jquants_ingest_gated_smoke.yaml"
POLICY = CONFIG_DIR / "operator_runner_policy.yaml"


@pytest.fixture
def gated_task_path(tmp_path: Path) -> Path:
    """Fast gated task with zero delay for tests."""
    path = tmp_path / "gated_fast.yaml"
    path.write_text(
        """
task_id: gated_fast_test
version: ops_task.v2
description: fast gated ingest test
risk_class: gated_ingest
simulate: true
steps:
  - id: ingest_three
    kind: gated_ingest_batch
    symbols: ["7011", "7203", "6501"]
    batch_size: 1
    delay_seconds: 0
    simulate: true
    output_artifact: ingest_batch_results.json
""".strip(),
        encoding="utf-8",
    )
    return path


def test_gated_task_yaml_loads() -> None:
    task = load_operator_task(GATED_TASK)
    assert task.task_id == "r7_0_jquants_ingest_gated_smoke"
    assert task.risk_class == "gated_ingest"
    assert task.steps[0].batch_size == 1
    assert task.steps[0].delay_seconds == 120


def test_dry_run_gated_ingest_planned_only(tmp_path: Path, gated_task_path: Path) -> None:
    state = run_operator_task(
        task_path=gated_task_path,
        policy_path=POLICY,
        mode="dry_run",
        outputs_root=tmp_path,
    )
    run_dir = tmp_path / "operator" / "runner" / state.task_id / state.run_id
    cp = json.loads((run_dir / "checkpoint.json").read_text(encoding="utf-8"))
    assert cp["steps"][0]["status"] == "planned"
    assert not (run_dir / "ingest_progress.json").exists()
    ev = json.loads((run_dir / "evidence_summary.json").read_text(encoding="utf-8"))
    assert ev["steps_completed"] == 0


def test_execute_readonly_rejects_gated_task(tmp_path: Path, gated_task_path: Path) -> None:
    with pytest.raises(RunnerStop, match="execute_readonly cannot run gated_ingest"):
        run_operator_task(
            task_path=gated_task_path,
            policy_path=POLICY,
            mode="execute_readonly",
            outputs_root=tmp_path,
        )


def test_execute_gated_missing_gates_blocked(tmp_path: Path, gated_task_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("CONFIRM_LIVE_HTTP", "CONFIRM_CACHE_WRITE", "CONFIRM_OPERATOR_GATED_INGEST"):
        monkeypatch.delenv(key, raising=False)
    state = run_operator_task(
        task_path=gated_task_path,
        policy_path=POLICY,
        mode="execute_gated",
        outputs_root=tmp_path,
    )
    assert state.status == "blocked"
    assert state.blocked_count == 3
    assert state.completed_count == 0
    ev = json.loads(
        (tmp_path / "operator" / "runner" / state.task_id / state.run_id / "evidence_summary.json").read_text()
    )
    assert ev["gate_status"]["CONFIRM_LIVE_HTTP"] is False


def test_execute_gated_with_gates_simulates(tmp_path: Path, gated_task_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_LIVE_HTTP", "YES")
    monkeypatch.setenv("CONFIRM_CACHE_WRITE", "YES")
    monkeypatch.setenv("CONFIRM_OPERATOR_GATED_INGEST", "YES")
    state = run_operator_task(
        task_path=gated_task_path,
        policy_path=POLICY,
        mode="execute_gated",
        outputs_root=tmp_path,
    )
    assert state.status == "completed"
    assert state.completed_count == 3
    run_dir = tmp_path / "operator" / "runner" / state.task_id / state.run_id
    progress = load_ingest_progress(run_dir)
    assert progress.completed_symbols == ["7011", "7203", "6501"]


def test_http_429_stops_batch(tmp_path: Path, gated_task_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_LIVE_HTTP", "YES")
    monkeypatch.setenv("CONFIRM_CACHE_WRITE", "YES")
    monkeypatch.setenv("CONFIRM_OPERATOR_GATED_INGEST", "YES")

    calls: list[str] = []

    def flaky_executor(symbol: str) -> SymbolBatchResult:
        calls.append(symbol)
        if symbol == "7203":
            return SymbolBatchResult(symbol=symbol, status="failed", detail="http_status_429 rate limited")
        return SymbolBatchResult(symbol=symbol, status="completed", detail="ok", simulated=True)

    with pytest.raises(RunnerStop, match="stop_on_http_marker"):
        run_operator_task(
            task_path=gated_task_path,
            policy_path=POLICY,
            mode="execute_gated",
            outputs_root=tmp_path,
            ingest_executor=flaky_executor,
        )
    assert calls == ["7011", "7203"]


def test_checkpoint_resume_skips_completed(tmp_path: Path, gated_task_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_LIVE_HTTP", "YES")
    monkeypatch.setenv("CONFIRM_CACHE_WRITE", "YES")
    monkeypatch.setenv("CONFIRM_OPERATOR_GATED_INGEST", "YES")

    seen: list[str] = []

    def counting_executor(symbol: str) -> SymbolBatchResult:
        seen.append(symbol)
        if symbol == "7203":
            return SymbolBatchResult(symbol=symbol, status="failed", detail="http_status_429")
        return SymbolBatchResult(symbol=symbol, status="completed", detail="ok", simulated=True)

    with pytest.raises(RunnerStop):
        run_operator_task(
            task_path=gated_task_path,
            policy_path=POLICY,
            mode="execute_gated",
            outputs_root=tmp_path,
            ingest_executor=counting_executor,
        )
    run_dirs = list((tmp_path / "operator" / "runner" / "gated_fast_test").iterdir())
    run_dir = run_dirs[0]
    progress = load_ingest_progress(run_dir)
    assert progress.completed_symbols == ["7011"]

    second_seen: list[str] = []

    def resume_executor(symbol: str) -> SymbolBatchResult:
        second_seen.append(symbol)
        return SymbolBatchResult(symbol=symbol, status="completed", detail="ok", simulated=True)

    state = run_operator_task(
        task_path=gated_task_path,
        policy_path=POLICY,
        mode="execute_gated",
        outputs_root=tmp_path,
        resume_run_dir=run_dir,
        ingest_executor=resume_executor,
    )
    assert "7011" not in second_seen
    assert set(second_seen) == {"7203", "6501"}
    assert state.completed_count == 2


def test_gate_missing_individual_env(tmp_path: Path, gated_task_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIRM_LIVE_HTTP", "YES")
    monkeypatch.setenv("CONFIRM_CACHE_WRITE", "YES")
    monkeypatch.delenv("CONFIRM_OPERATOR_GATED_INGEST", raising=False)
    state = run_operator_task(
        task_path=gated_task_path,
        policy_path=POLICY,
        mode="execute_gated",
        outputs_root=tmp_path,
    )
    assert state.status == "blocked"
    assert state.gate_status["CONFIRM_OPERATOR_GATED_INGEST"] is False
