"""Policy-gated local operator task runner (dry-run default)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from invis_alpha_os.config.paths import CONFIG_DIR, OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.discovery.cross_market_contract import (
    assert_no_forbidden_terms,
    merge_cross_market_json_payloads,
)
from invis_alpha_os.operator.gated_ingest import (
    IngestExecutor,
    check_gated_ingest_gates,
    run_gated_ingest_batch,
)
from invis_alpha_os.operator.policy import OperatorRunnerPolicy, load_operator_runner_policy
from invis_alpha_os.operator.task_spec import OperatorTaskSpec, OperatorTaskStep, load_operator_task

RunMode = Literal["dry_run", "execute_readonly", "execute_gated"]

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
    attempted_count: int = 0
    completed_count: int = 0
    blocked_count: int = 0


@dataclass
class RunState:
    task_id: str
    run_id: str
    mode: RunMode
    started_at: str
    policy_version: str
    task_version: str
    ended_at: str = ""
    status: str = "running"
    stop_reason: str = ""
    gate_status: dict[str, bool] = field(default_factory=dict)
    attempted_count: int = 0
    completed_count: int = 0
    blocked_count: int = 0
    steps: list[StepRecord] = field(default_factory=list)


def default_policy_path() -> Path:
    return CONFIG_DIR / "operator_runner_policy.yaml"


def default_task_path() -> Path:
    return CONFIG_DIR / "tasks" / "r7_0_discovery_readonly_smoke.yaml"


def default_gated_task_path() -> Path:
    return CONFIG_DIR / "tasks" / "r7_0_jquants_ingest_gated_smoke.yaml"


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_gated_step(step: OperatorTaskStep) -> bool:
    return step.kind == "gated_ingest_batch" or step.risk_class == "gated_ingest"


def _args_contain_forbidden(flags: tuple[str, ...], forbidden: tuple[str, ...]) -> str | None:
    for arg in flags:
        for bad in forbidden:
            if arg == bad or arg.startswith(f"{bad}="):
                return bad
    return None


def _scan_http_stop(text: str, policy: OperatorRunnerPolicy) -> list[int]:
    hits: list[int] = []
    for code in policy.stop_on_http_status:
        if re.search(rf"\b{code}\b", text):
            hits.append(code)
    for marker in policy.stop_on_http_markers:
        if marker in text and marker not in {str(c) for c in hits}:
            if marker.isdigit():
                hits.append(int(marker))
    return hits


def _validate_step_against_policy(step: OperatorTaskStep, policy: OperatorRunnerPolicy) -> None:
    if step.kind not in policy.allowed_step_kinds:
        raise RunnerStop(f"step kind not allowed: {step.kind}", step_id=step.step_id)
    bad = _args_contain_forbidden(step.args, policy.forbidden_cli_flags)
    if bad:
        raise RunnerStop(f"forbidden cli flag in step args: {bad}", step_id=step.step_id)


def _check_stdout_policy(text: str, policy: OperatorRunnerPolicy, *, step_id: str) -> None:
    if len(text.encode("utf-8")) > policy.max_step_stdout_bytes:
        raise RunnerStop("step stdout exceeds max_step_stdout_bytes", step_id=step_id)
    hits = _scan_http_stop(text, policy)
    if hits:
        raise RunnerStop(f"stop_on_http_status matched: {hits}", step_id=step_id)
    for marker in policy.stop_on_http_markers:
        if marker in text:
            raise RunnerStop(f"stop_on_http_marker matched: {marker}", step_id=step_id)
    if policy.forbidden_output_terms_check:
        try:
            assert_no_forbidden_terms(text)
        except ValueError as e:
            raise RunnerStop(str(e), step_id=step_id) from e


def _run_cli_step(
    *,
    step: OperatorTaskStep,
    run_dir: Path,
    repo_root: Path,
    policy: OperatorRunnerPolicy,
) -> StepRecord:
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
        attempted_count=1,
        completed_count=1,
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
        attempted_count=1,
        completed_count=1,
    )


def _run_gated_ingest_step(
    *,
    step: OperatorTaskStep,
    run_dir: Path,
    policy: OperatorRunnerPolicy,
    mode: RunMode,
    gate_check: Any,
    ingest_executor: IngestExecutor | None,
    sleep_fn: Callable[[float], None] | None,
) -> StepRecord:
    if not step.symbols:
        raise RunnerStop("gated_ingest_batch requires symbols", step_id=step.step_id)
    if mode == "execute_readonly":
        return StepRecord(
            step_id=step.step_id,
            kind=step.kind,
            status="blocked",
            detail="execute_readonly cannot run gated ingest",
            output_artifact=step.output_artifact,
            attempted_count=len(step.symbols),
            blocked_count=len(step.symbols),
        )
    if mode == "dry_run":
        return StepRecord(
            step_id=step.step_id,
            kind=step.kind,
            status="planned",
            detail="dry_run — gated ingest not executed",
            output_artifact=step.output_artifact,
            attempted_count=len(step.symbols),
        )

    batch_results, progress, stop_reason = run_gated_ingest_batch(
        step_id=step.step_id,
        symbols=list(step.symbols),
        batch_size=step.batch_size,
        delay_seconds=step.delay_seconds,
        run_dir=run_dir,
        policy=policy,
        gates_ok=gate_check.ok,
        gate_status=gate_check.status,
        simulate=step.simulate,
        executor=ingest_executor,
        sleep_fn=sleep_fn,
    )
    completed = sum(1 for r in batch_results if r.status == "completed")
    blocked = sum(1 for r in batch_results if r.status == "blocked")
    attempted = len(batch_results)
    if step.output_artifact:
        payload = {
            "step_id": step.step_id,
            "simulate": step.simulate,
            "results": [asdict(r) for r in batch_results],
            "progress": asdict(progress),
        }
        (run_dir / step.output_artifact).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if stop_reason:
        raise RunnerStop(stop_reason, step_id=step.step_id)
    status = "blocked" if not gate_check.ok else "completed"
    return StepRecord(
        step_id=step.step_id,
        kind=step.kind,
        status=status,
        detail="gated ingest batch",
        output_artifact=step.output_artifact,
        attempted_count=attempted,
        completed_count=completed,
        blocked_count=blocked,
    )


def _write_checkpoint(run_dir: Path, state: RunState) -> Path:
    path = run_dir / "checkpoint.json"
    payload = {
        "task_id": state.task_id,
        "run_id": state.run_id,
        "mode": state.mode,
        "started_at": state.started_at,
        "ended_at": state.ended_at,
        "status": state.status,
        "stop_reason": state.stop_reason,
        "policy_version": state.policy_version,
        "task_version": state.task_version,
        "gate_status": state.gate_status,
        "attempted_count": state.attempted_count,
        "completed_count": state.completed_count,
        "blocked_count": state.blocked_count,
        "steps": [asdict(s) for s in state.steps],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _write_evidence_summary(run_dir: Path, state: RunState, task: OperatorTaskSpec) -> None:
    completed_steps = [s for s in state.steps if s.status == "completed"]
    summary = {
        "task_id": state.task_id,
        "run_id": state.run_id,
        "mode": state.mode,
        "status": state.status,
        "stop_reason": state.stop_reason,
        "description": task.description,
        "started_at": state.started_at,
        "ended_at": state.ended_at or _utc_now_iso(),
        "gate_status": state.gate_status,
        "steps_total": len(task.steps),
        "steps_completed": len(completed_steps),
        "attempted_count": state.attempted_count,
        "completed_count": state.completed_count,
        "blocked_count": state.blocked_count,
        "artifacts": [s.output_artifact for s in completed_steps if s.output_artifact],
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
        f"- attempted: {state.attempted_count}",
        f"- completed: {state.completed_count}",
        f"- blocked: {state.blocked_count}",
    ]
    if state.gate_status:
        lines.append(f"- gate_status: {state.gate_status}")
    if state.stop_reason:
        lines.append(f"- stop_reason: {state.stop_reason}")
    lines.extend(["", "## Steps", ""])
    for rec in state.steps:
        lines.append(f"- **{rec.step_id}** — {rec.status}: {rec.detail or rec.kind}")
    lines.append("")
    (run_dir / "evidence_summary.md").write_text("\n".join(lines), encoding="utf-8")


def _accumulate_counts(state: RunState, rec: StepRecord) -> None:
    state.attempted_count += rec.attempted_count
    state.completed_count += rec.completed_count
    state.blocked_count += rec.blocked_count


def run_operator_task(
    *,
    task_path: Path,
    policy_path: Path | None = None,
    mode: RunMode | None = None,
    repo_root: Path | None = None,
    outputs_root: Path | None = None,
    resume_run_dir: Path | None = None,
    ingest_executor: IngestExecutor | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> RunState:
    """Run task under policy. Default mode is dry_run (plan only, no subprocess)."""
    root = repo_root or ROOT_DIR
    policy = load_operator_runner_policy(policy_path or default_policy_path())
    task = load_operator_task(task_path)
    if mode is not None:
        effective_mode: RunMode = mode
    elif policy.default_mode == "execute_readonly":
        effective_mode = "execute_readonly"
    elif policy.default_mode == "execute_gated":
        effective_mode = "execute_gated"
    else:
        effective_mode = "dry_run"

    if task.risk_class == "gated_ingest" and effective_mode == "execute_readonly":
        raise RunnerStop("execute_readonly cannot run gated_ingest task")

    gate_check = check_gated_ingest_gates(policy) if effective_mode == "execute_gated" else None

    if resume_run_dir is not None:
        out_base = resume_run_dir
        run_id = out_base.name
        started_at = run_id
    else:
        run_id = _utc_run_id()
        out_base = (outputs_root or OUTPUTS_DIR) / RUNNER_REL_ROOT / task.task_id / run_id
        started_at = run_id
    out_base.mkdir(parents=True, exist_ok=True)

    state = RunState(
        task_id=task.task_id,
        run_id=run_id,
        mode=effective_mode,
        started_at=started_at,
        policy_version=policy.version,
        task_version=task.version,
        gate_status=gate_check.status if gate_check else {},
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
                    attempted_count=len(step.symbols) if _is_gated_step(step) else 0,
                )
                state.steps.append(rec)
                _accumulate_counts(state, rec)
                _write_checkpoint(out_base, state)
                continue

            if _is_gated_step(step):
                rec = _run_gated_ingest_step(
                    step=step,
                    run_dir=out_base,
                    policy=policy,
                    mode=effective_mode,
                    gate_check=gate_check,
                    ingest_executor=ingest_executor,
                    sleep_fn=sleep_fn,
                )
            elif step.kind == "cli":
                rec = _run_cli_step(step=step, run_dir=out_base, repo_root=root, policy=policy)
            elif step.kind == "merge_discovery_json":
                rec = _run_merge_discovery_step(step=step, run_dir=out_base, policy=policy)
            else:
                raise RunnerStop(f"unknown step kind: {step.kind}", step_id=step.step_id)

            state.steps.append(rec)
            _accumulate_counts(state, rec)
            _write_checkpoint(out_base, state)

        state.status = "blocked" if state.blocked_count and not state.completed_count else "completed"
        if gate_check and not gate_check.ok and effective_mode == "execute_gated":
            state.status = "blocked"
    except RunnerStop as e:
        state.status = "stopped"
        state.stop_reason = e.reason
        if e.step_id and not any(s.step_id == e.step_id and s.status == "stopped" for s in state.steps):
            state.steps.append(
                StepRecord(step_id=e.step_id, kind="?", status="stopped", detail=e.reason)
            )
        state.ended_at = _utc_now_iso()
        _write_checkpoint(out_base, state)
        _write_evidence_summary(out_base, state, task)
        raise

    state.ended_at = _utc_now_iso()
    _write_checkpoint(out_base, state)
    _write_evidence_summary(out_base, state, task)
    return state
