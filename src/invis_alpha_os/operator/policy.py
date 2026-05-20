"""Load and validate operator runner safety policy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.config.loader import load_yaml


@dataclass(frozen=True)
class GateSpec:
    env_var: str
    required_value: str


@dataclass(frozen=True)
class OperatorRunnerPolicy:
    version: str
    default_mode: str
    live_http_gate: GateSpec
    cache_write_gate: GateSpec
    stop_on_http_status: tuple[int, ...]
    forbidden_cli_flags: tuple[str, ...]
    forbidden_commit_path_prefixes: tuple[str, ...]
    forbidden_output_terms_check: bool
    max_step_stdout_bytes: int
    allowed_step_kinds: tuple[str, ...]

    def gate_satisfied(self, gate: GateSpec) -> bool:
        return os.environ.get(gate.env_var, "").strip() == gate.required_value


def _gate_from_mapping(data: dict[str, Any], key: str, *, default_env: str) -> GateSpec:
    block = data.get(key) or {}
    if not isinstance(block, dict):
        block = {}
    return GateSpec(
        env_var=str(block.get("env_var") or default_env),
        required_value=str(block.get("required_value") or "YES"),
    )


def load_operator_runner_policy(path: Path) -> OperatorRunnerPolicy:
    raw = load_yaml(path)
    gates = raw.get("gates") or {}
    if not isinstance(gates, dict):
        gates = {}
    stop_raw = raw.get("stop_on_http_status") or [400, 429]
    stop_on = tuple(int(x) for x in stop_raw)
    flags_raw = raw.get("forbidden_cli_flags") or []
    forbidden_flags = tuple(str(x) for x in flags_raw)
    prefixes_raw = raw.get("forbidden_commit_path_prefixes") or []
    prefixes = tuple(str(x) for x in prefixes_raw)
    kinds_raw = raw.get("allowed_step_kinds") or ["cli", "merge_discovery_json"]
    kinds = tuple(str(x) for x in kinds_raw)
    return OperatorRunnerPolicy(
        version=str(raw.get("version") or "ops_runner_policy.v1"),
        default_mode=str(raw.get("default_mode") or "dry_run"),
        live_http_gate=_gate_from_mapping(gates, "live_http", default_env="CONFIRM_LIVE_HTTP"),
        cache_write_gate=_gate_from_mapping(gates, "cache_write", default_env="CONFIRM_CACHE_WRITE"),
        stop_on_http_status=stop_on,
        forbidden_cli_flags=forbidden_flags,
        forbidden_commit_path_prefixes=prefixes,
        forbidden_output_terms_check=bool(raw.get("forbidden_output_terms_check", True)),
        max_step_stdout_bytes=int(raw.get("max_step_stdout_bytes") or 500_000),
        allowed_step_kinds=kinds,
    )
