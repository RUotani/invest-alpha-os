"""Gated ingest batch execution (simulation-first; no ungated live HTTP)."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

from invis_alpha_os.operator.policy import GateSpec, OperatorRunnerPolicy

INGEST_PROGRESS_FILE = "ingest_progress.json"


@dataclass
class GateCheckResult:
    ok: bool
    missing: list[str] = field(default_factory=list)
    status: dict[str, bool] = field(default_factory=dict)


@dataclass
class SymbolBatchResult:
    symbol: str
    status: str
    detail: str = ""
    simulated: bool = True


@dataclass
class IngestProgress:
    completed_symbols: list[str] = field(default_factory=list)
    blocked_symbols: list[str] = field(default_factory=list)
    failed_symbols: list[str] = field(default_factory=list)
    batches: list[dict[str, Any]] = field(default_factory=list)
    last_stopped_reason: str = ""


class IngestExecutor(Protocol):
    def __call__(self, symbol: str) -> SymbolBatchResult: ...


def gated_ingest_gates(policy: OperatorRunnerPolicy) -> tuple[GateSpec, ...]:
    return (policy.live_http_gate, policy.cache_write_gate, policy.gated_ingest_gate)


def check_gated_ingest_gates(policy: OperatorRunnerPolicy) -> GateCheckResult:
    missing: list[str] = []
    status: dict[str, bool] = {}
    for gate in gated_ingest_gates(policy):
        ok = policy.gate_satisfied(gate)
        status[gate.env_var] = ok
        if not ok:
            missing.append(gate.env_var)
    return GateCheckResult(ok=not missing, missing=missing, status=status)


def ingest_progress_path(run_dir: Path) -> Path:
    return run_dir / INGEST_PROGRESS_FILE


def load_ingest_progress(run_dir: Path) -> IngestProgress:
    path = ingest_progress_path(run_dir)
    if not path.is_file():
        return IngestProgress()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return IngestProgress(
        completed_symbols=list(raw.get("completed_symbols") or []),
        blocked_symbols=list(raw.get("blocked_symbols") or []),
        failed_symbols=list(raw.get("failed_symbols") or []),
        batches=list(raw.get("batches") or []),
        last_stopped_reason=str(raw.get("last_stopped_reason") or ""),
    )


def save_ingest_progress(run_dir: Path, progress: IngestProgress) -> None:
    ingest_progress_path(run_dir).write_text(
        json.dumps(asdict(progress), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def simulate_ingest_symbol(symbol: str) -> SymbolBatchResult:
    return SymbolBatchResult(
        symbol=symbol,
        status="completed",
        detail="simulated ingest (no live HTTP)",
        simulated=True,
    )


def run_gated_ingest_batch(
    *,
    step_id: str,
    symbols: list[str],
    batch_size: int,
    delay_seconds: int,
    run_dir: Path,
    policy: OperatorRunnerPolicy,
    gates_ok: bool,
    gate_status: dict[str, bool],
    simulate: bool,
    executor: IngestExecutor | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> tuple[list[SymbolBatchResult], IngestProgress, str | None]:
    """Run or simulate batched ingest. Returns (results, progress, stop_reason)."""
    progress = load_ingest_progress(run_dir)
    results: list[SymbolBatchResult] = []
    if not gates_ok:
        for sym in symbols:
            if sym in progress.completed_symbols or sym in progress.blocked_symbols:
                continue
            progress.blocked_symbols.append(sym)
            results.append(
                SymbolBatchResult(
                    symbol=sym,
                    status="blocked",
                    detail=f"gates missing: {', '.join(k for k, v in gate_status.items() if not v)}",
                    simulated=simulate,
                )
            )
        save_ingest_progress(run_dir, progress)
        return results, progress, None

    exec_fn = executor or simulate_ingest_symbol
    sleep = sleep_fn or time.sleep
    pending = [s for s in symbols if s not in progress.completed_symbols]
    for i, sym in enumerate(pending):
        if batch_size > 0 and i > 0 and i % batch_size == 0 and delay_seconds > 0:
            sleep(float(delay_seconds))
        batch_result = exec_fn(sym)
        results.append(batch_result)
        batch_record = {
            "step_id": step_id,
            "symbol": sym,
            "status": batch_result.status,
            "detail": batch_result.detail,
            "simulated": batch_result.simulated,
        }
        progress.batches.append(batch_record)
        if batch_result.status == "completed":
            progress.completed_symbols.append(sym)
        elif batch_result.status == "blocked":
            progress.blocked_symbols.append(sym)
        else:
            progress.failed_symbols.append(sym)
        save_ingest_progress(run_dir, progress)
        combined = batch_result.detail
        for marker in policy.stop_on_http_markers:
            if marker in combined:
                progress.last_stopped_reason = f"stop_on_http_marker matched: {marker}"
                save_ingest_progress(run_dir, progress)
                return results, progress, progress.last_stopped_reason
    return results, progress, None
