"""Wire gated ingest batches to J-Quants cache ingest CLI (command construction + gated subprocess)."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from invis_alpha_os.operator.gated_ingest import IngestExecutor, SymbolBatchResult, simulate_ingest_symbol
from invis_alpha_os.operator.policy import OperatorRunnerPolicy

JQUANTS_WATCHLIST_BARS_CACHE = "jquants-watchlist-bars-cache"


@dataclass(frozen=True)
class JquantsIngestWiring:
    cli_subcommand: str
    from_date: str
    to_date: str


def build_jquants_ingest_cli_argv(
    *,
    symbol: str,
    wiring: JquantsIngestWiring,
    include_live_flags: bool,
) -> list[str]:
    """Build argv for one-symbol J-Quants watchlist bars cache ingest."""
    if wiring.cli_subcommand != JQUANTS_WATCHLIST_BARS_CACHE:
        raise ValueError(f"unsupported ingest cli: {wiring.cli_subcommand}")
    argv = [
        sys.executable,
        "-m",
        "invis_alpha_os.cli.main",
        "debug",
        wiring.cli_subcommand,
        "--from-date",
        wiring.from_date,
        "--to-date",
        wiring.to_date,
        "--codes",
        symbol,
        "--limit",
        "1",
    ]
    if include_live_flags:
        argv.extend(["--live", "--write-cache"])
    return argv


def command_template_for_symbol(
    *,
    symbol: str,
    wiring: JquantsIngestWiring,
    include_live_flags: bool,
) -> str:
    parts = build_jquants_ingest_cli_argv(
        symbol=symbol,
        wiring=wiring,
        include_live_flags=include_live_flags,
    )
    # Drop python path for human-readable evidence (no secrets).
    return " ".join(parts[2:])


def _parse_cli_json(stdout: str) -> dict:
    text = stdout.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def run_jquants_ingest_subprocess(
    *,
    symbol: str,
    wiring: JquantsIngestWiring,
    repo_root: Path,
    include_live_flags: bool,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> SymbolBatchResult:
    """Execute wired J-Quants ingest CLI for one symbol (gated live+cache flags)."""
    cmd = build_jquants_ingest_cli_argv(
        symbol=symbol,
        wiring=wiring,
        include_live_flags=include_live_flags,
    )
    runner = subprocess_run or subprocess.run
    proc = runner(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    combined = (proc.stdout or "") + ("\n" + (proc.stderr or "") if proc.stderr else "")
    payload = _parse_cli_json(proc.stdout or "")
    status_field = str(payload.get("status", "")).strip()
    if proc.returncode == 0 and status_field in ("", "success", "ok", "cache_written"):
        return SymbolBatchResult(
            symbol=symbol,
            status="completed",
            detail=f"cli exit 0 status={status_field or 'ok'}",
            simulated=False,
        )
    detail = status_field or f"cli exit {proc.returncode}"
    if "429" in combined or "http_status_429" in combined:
        detail = "http_status_429"
    elif "400" in combined or "http_status_400" in combined:
        detail = "http_status_400"
    return SymbolBatchResult(
        symbol=symbol,
        status="failed",
        detail=detail,
        simulated=False,
    )


def make_jquants_ingest_executor(
    *,
    wiring: JquantsIngestWiring,
    repo_root: Path,
    policy: OperatorRunnerPolicy,
    simulate: bool,
    gates_ok: bool,
    subprocess_run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> IngestExecutor:
    if simulate or not gates_ok:
        return simulate_ingest_symbol
    include_live = policy.gate_satisfied(policy.live_http_gate) and policy.gate_satisfied(
        policy.cache_write_gate
    )

    def _execute(symbol: str) -> SymbolBatchResult:
        return run_jquants_ingest_subprocess(
            symbol=symbol,
            wiring=wiring,
            repo_root=repo_root,
            include_live_flags=include_live,
            subprocess_run=subprocess_run,
        )

    return _execute
