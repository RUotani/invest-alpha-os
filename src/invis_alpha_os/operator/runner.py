"""Policy-gated local operator task runner (dry-run default)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.discovery.cross_market_contract import (
    assert_no_forbidden_terms,
    merge_cross_market_json_payloads,
)
from invis_alpha_os.operator.policy import OperatorRunnerPolicy, load_operator_runner_policy
from invis_alpha_os.operator.task_spec import OperatorTaskSpec, OperatorTaskStep, load_operator_task

RunMode = Literal["dry_run", "execute_readonly"]

RUNNER_REL_ROOT = Path("operator/runner")


class RunnerStop(Exception):
    """Stop runner immediately with a safe, non-secret reason."""

    def __init__(self, reason: str, *, step_id: str | None = None) -> None:
        self.reason = reason
        self.step_id = step_id
        super().__init__(reason)


@dataclass
class StepRecord:
    step_id: str
    kind: str
    status: str
    detail: str = ""
    output_artifact: str = ""
    http_status_hits: list[int] = field(default_factory=list)


@dataclass
class RunState:
    task_id: str
    run_id: str
    mode: RunMode
    started_at: str
    policy_version: str
    task_version: str
    status: str = "running"
    stop_reason: str = ""
    steps: list[StepRecord] = field(default_factory=list)


def default_policy_path() -> Path:
    return CONFIG_DIR / "operator_runner_policy.yaml"


def default_task_path() -> Path:
    return CONFIG_DIR / "tasks" / "r7_0_discovery_readonly_smoke.yaml"


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _args_contain_forbidden(flags: tuple[str, ...], forbidden: tuple[str, ...]) -> str | None:
    for arg in flags:
        for bad in forbidden:
            if arg == bad or arg.startswith(f"{bad}="):
                return bad
    return None


def _scan_http_stop(stdout: str, policy: OperatorRunnerPolicy) -> list[int]:
    hits: list[int] = []
    for code in policy.stop_on_http_status:
        if re.search(rf"\b{code}\b", stdout):
            hits.append(code)
    return hits


def _validate_step_against_policy(step: OperatorTaskStep, policy: OperatorRunnerPolicy) -> None:
    if step.kind not in policy.allowed_step_kinds:
        raise RunnerStop(f"step kind not allowed: {step.kind}", step_id=step.step_id)
    bad = _args_contain_forbidden(step.args, policy.forbidden_cli_flags)
    if bad:
        raise RunnerStop(f"forbidden cli flag in step args: {bad}", step_id=step.step_id)
    if step.risk_class in ("live_http", "cache_write"):
        raise RunnerStop(f"risk_class {step.risk_class} requires explicit gate (not in Ops-A MVP)", step_id=step.step_id)


def _require_readonly_gate(step: OperatorTaskStep, policy: OperatorRunnerPolicy) -> None:
    if step.risk_class == "live_http" and not policy.gate_satisfied(policy.live_http_gate):
        raise RunnerStop(
            f"live_http gate missing: set {policy.live_http_gate.env_var}={policy.live_http_gate.required_value}",
            step_id=step.step_id,
        )
    if step.risk_class == "cache_write" and not policy.gate_satisfied(policy.cache_write_gate):
        raise RunnerStop(
            f"cache_write gate missing: set {policy.cache_write_gate.env_var}={policy.cache_write_gate.required_value}",
            step_id=step.step_id,
        )


def _check_stdout_policy(stdout: str, policy: OperatorRunnerPolicy, *, step_id: str) -> None:
    if len(stdout.encode("utf-8")) > policy.max_step_stdout_bytes:
        raise RunnerStop("step stdout exceeds max_step_stdout_bytes", step_id=step_id)
    hits = _scan_http_stop(stdout, policy)
    if hits:
        raise RunnerStop(f"stop_on_http_status matched: {hits}", step_id=step_id)
    if policy.forbidden_output_terms_check:
        try:
            assert_no_forbidden_terms(stdout)
        except ValueError as e:
            raise RunnerStop(str(e), step_id=step_id) from e


def _run_cli_step(
    *,
    step: OperatorTaskStep,
    run_dir: Path,
    repo_root: Path,
    policy: OperatorRunnerPolicy,
) -> StepRecord:
    _require_readonly_gate(step, policy)
    if not step.command:
        raise RunnerStop("cli step missing command", step_id=step.step_id)
    cmd = [sys.executable, "-m", "invis_alpha_os.cli.main", step.command, *step.args]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    combined = stdout + ("\n" + stderr if stderr else "")
    _check_stdout_policy(combined, policy, step_id=step.step_id)
    if proc.returncode != 0:
        raise RunnerStop(f"cli exit {proc.returncode}", step_id=step.step_id)
    if not step.output_artifact:
        raise RunnerStop("cli step missing output_artifact", step_id=step.step_id)
    out_path = run_dir / step.output_artifact
    out_path.write_text(stdout, encoding="utf-8")
    return StepRecord(
        step_id=step.step_id,
        kind=step.kind,
        status="completed",
        detail=f"cli {step.command}",
        output_artifact=step.output_artifact,
        http_status_hits=_scan_http_stop(combined, policy),
    )


def _run_merge_discovery_step(
    *,
    step: OperatorTaskStep,
    run_dir: Path,
    policy: OperatorRunnerPolicy,
) -> StepRecord:
    if len(step.inputs) != 2:
        raise RunnerStop("merge_discovery_json requires exactly two inputs", step_id=step.step_id)
    jp_path = run_dir / step.inputs[0]
    us_path = run_dir / step.inputs[1]
    if not jp_path.is_file() or not us_path.is_file():
        raise RunnerStop("merge inputs missing on disk", step_id=step.step_id)
    jp_payload = json.loads(jp_path.read_text(encoding="utf-8"))
    us_payload = json.loads(us_path.read_text(encoding="utf-8"))
    merged = merge_cross_market_json_payloads(jp_payload, us_payload)
    blob = json.dumps(merged, ensure_ascii=False, indent=2)
    if policy.forbidden_output_terms_check:
        assert_no_forbidden_terms(blob)
    if not step.output_artifact:
        raise RunnerStop("merge step missing output_artifact", step_id=step.step_id)
    (run_dir / step.output_artifact).write_text(blob + "\n", encoding="utf-8")
    return StepRecord(
        step_id=step.step_id,
        kind=step.kind,
        status="completed",
        detail="merge_cross_market_json_payloads",
        output_artifact=step.output_artifact,
    )


def _write_checkpoint(run_dir: Path, state: RunState) -> Path:
    path = run_dir / "checkpoint.json"
    payload = {
        "task_id": state.task_id,
        "run_id": state.run_id,
        "mode": state.mode,
        "started_at": state.started_at,
        "status": state.status,
        "stop_reason": state.stop_reason,
        "policy_version": state.policy_version,
        "task_version": state.task_version,
        "steps": [asdict(s) for s in state.steps],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_evidence_summary(run_dir: Path, state: RunState, task: OperatorTaskSpec) -> None:
    completed = [s for s in state.steps if s.status == "completed"]
    summary = {
        "task_id": state.task_id,
        "run_id": state.run_id,
        "mode": state.mode,
        "status": state.status,
        "stop_reason": state.stop_reason,
        "description": task.description,
        "steps_total": len(task.steps),
        "steps_completed": len(completed),
        "artifacts": [s.output_artifact for s in completed if s.output_artifact],
    }
    (run_dir / "evidence_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Operator runner evidence summary",
        "",
        f"- task_id: `{state.task_id}`",
        f"- run_id: `{state.run_id}`",
        f"- mode: `{state.mode}`",
        f"- status: `{state.status}`",
        f"- steps_completed: {len(completed)}/{len(task.steps)}",
    ]
    if state.stop_reason:
        lines.append(f"- stop_reason: {state.stop_reason}")
    lines.extend(["", "## Steps", ""])
    for rec in state.steps:
        lines.append(f"- **{rec.step_id}** — {rec.status}: {rec.detail or rec.kind}")
    lines.append("")
    (run_dir / "evidence_summary.md").write_text("\n".join(lines), encoding="utf-8")


def run_operator_task(
    *,
    task_path: Path,
    policy_path: Path | None = None,
    mode: RunMode | None = None,
    repo_root: Path | None = None,
    outputs_root: Path | None = None,
) -> RunState:
    """Run task under policy. Default mode is dry_run (plan only, no subprocess)."""
    root = repo_root or ROOT_DIR
    policy = load_operator_runner_policy(policy_path or default_policy_path())
    task = load_operator_task(task_path)
    if mode is not None:
        effective_mode: RunMode = mode
    elif policy.default_mode == "execute_readonly":
        effective_mode = "execute_readonly"
    else:
        effective_mode = "dry_run"

    if task.risk_class != "readonly" and effective_mode == "execute_readonly":
        raise RunnerStop(f"execute_readonly requires task risk_class=readonly (got {task.risk_class})")

    run_id = _utc_run_id()
    out_base = (outputs_root or OUTPUTS_DIR) / RUNNER_REL_ROOT / task.task_id / run_id
    out_base.mkdir(parents=True, exist_ok=True)

    state = RunState(
        task_id=task.task_id,
        run_id=run_id,
        mode=effective_mode,
        started_at=run_id,
        policy_version=policy.version,
        task_version=task.version,
    )
    _write_checkpoint(out_base, state)

    try:
        for step in task.steps:
            _validate_step_against_policy(step, policy)
            if effective_mode == "dry_run":
                rec = StepRecord(
                    step_id=step.step_id,
                    kind=step.kind,
                    status="planned",
                    detail="dry_run — not executed",
                    output_artifact=step.output_artifact,
                )
                state.steps.append(rec)
                _write_checkpoint(out_base, state)
                continue

            if step.risk_class != "readonly" and task.risk_class != "readonly":
                _require_readonly_gate(step, policy)

            if step.kind == "cli":
                rec = _run_cli_step(step=step, run_dir=out_base, repo_root=root, policy=policy)
            elif step.kind == "merge_discovery_json":
                rec = _run_merge_discovery_step(step=step, run_dir=out_base, policy=policy)
            else:
                raise RunnerStop(f"unknown step kind: {step.kind}", step_id=step.step_id)

            state.steps.append(rec)
            _write_checkpoint(out_base, state)

        state.status = "completed"
    except RunnerStop as e:
        state.status = "stopped"
        state.stop_reason = e.reason
        if e.step_id:
            state.steps.append(
                StepRecord(step_id=e.step_id, kind="?", status="stopped", detail=e.reason)
            )
        _write_checkpoint(out_base, state)
        _write_evidence_summary(out_base, state, task)
        raise

    _write_checkpoint(out_base, state)
    _write_evidence_summary(out_base, state, task)
    return state
