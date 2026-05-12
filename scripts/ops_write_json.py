#!/usr/bin/env python3
"""Write ``outputs/ops/latest_ops_summary.json`` and ``latest_verdict.json`` (local-only; gitignored)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode",
        choices=("pytest", "ship", "momentum"),
        required=True,
        help="Which workflow produced this snapshot.",
    )
    p.add_argument("--pytest-exit", type=int, default=0)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory (default: <repo>/outputs/ops).",
    )
    ns = p.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    out_dir = ns.output_dir if ns.output_dir is not None else repo / "outputs" / "ops"
    out_dir.mkdir(parents=True, exist_ok=True)
    now = _utc_now()
    live_http = False

    summary: dict = {
        "schema_version": 1,
        "generated_at": now,
        "mode": ns.mode,
        "live_http_performed": live_http,
    }
    verdict: dict = {
        "schema_version": 1,
        "generated_at": now,
        "verdict": "pass",
        "reason": "",
        "live_http_performed": live_http,
    }

    if ns.mode == "pytest":
        summary["pytest_exit_code"] = ns.pytest_exit
        summary["pytest_passed"] = ns.pytest_exit == 0
        if ns.pytest_exit != 0:
            verdict["verdict"] = "fail"
            verdict["reason"] = f"pytest exit code {ns.pytest_exit}"
        else:
            verdict["reason"] = "pytest passed"
    elif ns.mode == "ship":
        summary["pipeline"] = "test_then_safe_push_then_post_push_check"
        verdict["reason"] = "ship: test + safe-push + post-push-check completed"
    elif ns.mode == "momentum":
        summary["check"] = "daily_momentum_check"
        verdict["reason"] = "daily-momentum-check completed (daily + grep excerpt)"

    od = out_dir / "latest_ops_summary.json"
    vd = out_dir / "latest_verdict.json"
    od.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    vd.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
