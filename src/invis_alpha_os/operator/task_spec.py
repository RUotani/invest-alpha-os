"""Load operator task YAML specifications."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.loader import load_yaml
from invis_alpha_os.operator.jquants_ingest_wiring import JquantsIngestWiring


@dataclass(frozen=True)
class OperatorTaskStep:
    step_id: str
    kind: str
    command: str
    args: tuple[str, ...]
    inputs: tuple[str, ...]
    output_artifact: str
    risk_class: str
    symbols: tuple[str, ...] = ()
    batch_size: int = 1
    delay_seconds: int = 0
    simulate: bool = True
    from_date: str = ""
    to_date: str = ""


@dataclass(frozen=True)
class OperatorTaskSpec:
    task_id: str
    version: str
    description: str
    risk_class: str
    simulate: bool
    ingest_batch_size: int
    ingest_delay_seconds: int
    ingest_wiring: JquantsIngestWiring | None
    steps: tuple[OperatorTaskStep, ...]


def resolve_step_wiring(task: OperatorTaskSpec, step: OperatorTaskStep) -> JquantsIngestWiring | None:
    base = task.ingest_wiring
    if base is None:
        return None
    from_date = step.from_date or base.from_date
    to_date = step.to_date or base.to_date
    if not from_date or not to_date:
        return None
    return JquantsIngestWiring(
        cli_subcommand=base.cli_subcommand,
        from_date=from_date,
        to_date=to_date,
    )


def _load_ingest_wiring(raw: dict[str, Any]) -> JquantsIngestWiring | None:
    block = raw.get("ingest_wiring")
    if not block:
        return None
    if not isinstance(block, dict):
        raise ValueError("ingest_wiring must be a mapping")
    cli = str(block.get("cli_subcommand") or "jquants-watchlist-bars-cache").strip()
    from_date = str(block.get("from_date") or "").strip()
    to_date = str(block.get("to_date") or "").strip()
    if not from_date or not to_date:
        raise ValueError("ingest_wiring requires from_date and to_date")
    return JquantsIngestWiring(cli_subcommand=cli, from_date=from_date, to_date=to_date)


def _step_from_mapping(
    data: dict[str, Any],
    *,
    default_risk: str,
    task_simulate: bool,
    ingest_batch_size: int,
    ingest_delay_seconds: int,
) -> OperatorTaskStep:
    args_raw = data.get("args") or []
    if not isinstance(args_raw, list):
        raise ValueError("step args must be a list")
    inputs_raw = data.get("inputs") or []
    if not isinstance(inputs_raw, list):
        raise ValueError("step inputs must be a list")
    symbols_raw = data.get("symbols") or []
    if not isinstance(symbols_raw, list):
        raise ValueError("step symbols must be a list")
    batch_size = int(data.get("batch_size", ingest_batch_size))
    delay_seconds = int(data.get("delay_seconds", ingest_delay_seconds))
    simulate = bool(data.get("simulate", task_simulate))
    return OperatorTaskStep(
        step_id=str(data.get("id") or "").strip(),
        kind=str(data.get("kind") or "").strip(),
        command=str(data.get("command") or "").strip(),
        args=tuple(str(a) for a in args_raw),
        inputs=tuple(str(x) for x in inputs_raw),
        output_artifact=str(data.get("output_artifact") or "").strip(),
        risk_class=str(data.get("risk_class") or default_risk).strip() or default_risk,
        symbols=tuple(str(s).strip() for s in symbols_raw if str(s).strip()),
        batch_size=batch_size,
        delay_seconds=delay_seconds,
        simulate=simulate,
        from_date=str(data.get("from_date") or "").strip(),
        to_date=str(data.get("to_date") or "").strip(),
    )


def load_operator_task(path: Path) -> OperatorTaskSpec:
    raw = load_yaml(path)
    task_id = str(raw.get("task_id") or "").strip()
    if not task_id:
        raise ValueError(f"task_id required: {path}")
    default_risk = str(raw.get("risk_class") or "readonly").strip() or "readonly"
    task_simulate = bool(raw.get("simulate", True))
    ingest_defaults = raw.get("ingest_defaults") or {}
    if not isinstance(ingest_defaults, dict):
        ingest_defaults = {}
    ingest_batch_size = int(ingest_defaults.get("batch_size", 1))
    ingest_delay_seconds = int(ingest_defaults.get("delay_seconds", 0))
    ingest_wiring = _load_ingest_wiring(raw)
    steps_raw = raw.get("steps") or []
    if not isinstance(steps_raw, list) or not steps_raw:
        raise ValueError(f"steps required: {path}")
    steps: list[OperatorTaskStep] = []
    for item in steps_raw:
        if not isinstance(item, dict):
            raise ValueError("each step must be a mapping")
        step = _step_from_mapping(
            item,
            default_risk=default_risk,
            task_simulate=task_simulate,
            ingest_batch_size=ingest_batch_size,
            ingest_delay_seconds=ingest_delay_seconds,
        )
        if not step.step_id or not step.kind:
            raise ValueError("step id and kind required")
        steps.append(step)
    return OperatorTaskSpec(
        task_id=task_id,
        version=str(raw.get("version") or "ops_task.v1"),
        description=str(raw.get("description") or "").strip(),
        risk_class=default_risk,
        simulate=task_simulate,
        ingest_batch_size=ingest_batch_size,
        ingest_delay_seconds=ingest_delay_seconds,
        ingest_wiring=ingest_wiring,
        steps=tuple(steps),
    )
