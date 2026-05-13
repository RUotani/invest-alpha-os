#!/usr/bin/env python3
"""Write ``outputs/ops/latest_ops_summary.json`` and ``latest_verdict.json`` (local-only; gitignored)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_JQ_LIVE_RESULT_FORBIDDEN_KEYS = frozenset(
    {
        "error_body_preview",
        "error_kind",
        "raw_response",
        "raw_body",
        "headers",
        "authorization",
        "x-api-key",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "cookie",
        "cookies",
        "set-cookie",
        "bearer",
        "evil_raw_body",
        "full_url",
        "full_url_without_secrets",
        "query_params",
        "endpoint_url",
        "api_key_header_name",
    }
)

_JQ_OPS_SUMMARY_RESULT_ORDER = (
    "code",
    "status",
    "http_status",
    "reason",
    "row_count",
    "sanitized_bar_count",
    "cache_written_to",
    "raw_response_included",
)


def sanitize_jquants_live_results_for_ops_summary(results: list[Any]) -> list[dict[str, Any]]:
    """Copy only operator-safe keys; force ``raw_response_included`` False for persisted ops summary."""

    out: list[dict[str, Any]] = []
    for r in results:
        if not isinstance(r, dict):
            continue
        row: dict[str, Any] = {}
        for k in _JQ_OPS_SUMMARY_RESULT_ORDER:
            if k == "raw_response_included":
                row[k] = False
            elif k in r:
                row[k] = r[k]
        out.append(row)
    return out


def validate_jquants_live_result_rows(results: list[Any]) -> str | None:
    for i, row in enumerate(results):
        if not isinstance(row, dict):
            return f"result_row_not_object:{i}"
        if row.get("raw_response_included") is True:
            return f"row_raw_response_true:{i}"
        for k in row:
            if str(k).lower() in _JQ_LIVE_RESULT_FORBIDDEN_KEYS:
                return f"row_forbidden_field:{i}:{k}"
    return None


def validate_jquants_watchlist_cache_live_payload(payload: dict[str, Any]) -> str | None:
    """Return error token unless payload is CLI ``completed`` bulk live stdout (never dry_run / validation_error)."""

    if not isinstance(payload, dict):
        return "payload_not_object"
    if payload.get("status") != "completed":
        return f"invalid_status:{payload.get('status')!r}"
    mod = payload.get("mode")
    if mod is not None and mod != "jquants_watchlist_cache_live":
        return f"invalid_mode:{mod!r}"
    if payload.get("raw_response_included") is not False:
        return "raw_response_not_false_or_missing"
    if not isinstance(payload.get("results"), list):
        return "results_not_list"
    row_err = validate_jquants_live_result_rows(payload["results"])
    if row_err is not None:
        return row_err
    for key in ("success_count", "error_count", "skipped_count", "cache_written_count"):
        val = payload.get(key)
        if not isinstance(val, int) or val < 0:
            return f"bad_count:{key}"
    tc = payload.get("target_count")
    if not isinstance(tc, int) or tc < 1:
        return "bad_target_count"
    df = payload.get("date_from")
    dt_to = payload.get("date_to")
    if not isinstance(df, str) or not df.strip():
        return "bad_date_from"
    if not isinstance(dt_to, str) or not dt_to.strip():
        return "bad_date_to"
    if payload.get("live_http_performed") is not True:
        return "live_http_not_true"
    return None


def verdict_jquants_watchlist_cache_live(payload: dict[str, Any]) -> tuple[str, str]:
    """Rules for ``jquants_watchlist_cache_live`` (must match product expectations)."""

    results = payload.get("results") or []
    unknown = any(
        r.get("status") == "http_error" and r.get("reason") == "http_error_unknown" for r in results
    )
    if unknown:
        return "needs_human_review", "http_error rows with unknown reason"

    err = int(payload.get("error_count", 0))
    succ = int(payload.get("success_count", 0))
    cw = int(payload.get("cache_written_count", 0))
    if err > 0 and succ == 0:
        return "fail", "all non-skipped targets failed"
    if succ == 0 and err == 0:
        return "fail", "no successful live targets (empty or non-success rows only)"
    if succ > 0 and err > 0:
        return "partial_success", "some non-skipped targets failed"
    if err == 0 and succ > 0 and cw == succ:
        return "pass", "all successes and cache writes aligned"
    if err == 0 and succ > 0 and cw != succ:
        return "partial_success", "successes but cache_written_count does not match success_count"
    return "fail", "unexpected state"


def _read_payload_payload_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode",
        choices=("pytest", "ship", "momentum", "jquants_watchlist_cache_live"),
        required=True,
        help="Which workflow produced this snapshot.",
    )
    p.add_argument("--pytest-exit", type=int, default=0)
    p.add_argument(
        "--payload-file",
        type=Path,
        default=None,
        help="JSON payload (e.g. stdout from jquants-watchlist-bars-cache). Use - for stdin.",
    )
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

    summary: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": now,
        "mode": ns.mode,
        "live_http_performed": live_http,
    }
    verdict: dict[str, Any] = {
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
    elif ns.mode == "jquants_watchlist_cache_live":
        if ns.payload_file is None:
            print("ops_write_json: --payload-file required for jquants_watchlist_cache_live", file=sys.stderr)
            return 2
        if str(ns.payload_file) == "-":
            raw = sys.stdin.read()
            payload = json.loads(raw)
        else:
            payload = _read_payload_payload_file(ns.payload_file)
        perr = validate_jquants_watchlist_cache_live_payload(payload)
        if perr is not None:
            print(f"ops_write_json: invalid jquants_watchlist_cache_live payload ({perr})", file=sys.stderr)
            return 3
        failed = payload.get("failed_codes")
        if not isinstance(failed, list):
            failed = [str(r.get("code")) for r in (payload.get("results") or []) if r.get("status") != "success"]
        v_text, v_reason = verdict_jquants_watchlist_cache_live(payload)
        summary.update(
            {
                "mode": "jquants_watchlist_cache_live",
                "target_count": int(payload.get("target_count", 0)),
                "success_count": int(payload.get("success_count", 0)),
                "error_count": int(payload.get("error_count", 0)),
                "skipped_count": int(payload.get("skipped_count", 0)),
                "cache_written_count": int(payload.get("cache_written_count", 0)),
                "failed_codes": failed,
                "live_http_performed": bool(payload.get("live_http_performed", True)),
                "raw_response_included": False,
                "date_from": payload.get("date_from"),
                "date_to": payload.get("date_to"),
            }
        )
        crq = payload.get("codes_requested")
        if isinstance(crq, str) and crq.strip():
            summary["codes_requested"] = crq.strip()
        verdict["verdict"] = v_text
        verdict["reason"] = v_reason
        verdict["live_http_performed"] = summary["live_http_performed"]
        summary["results"] = sanitize_jquants_live_results_for_ops_summary(payload.get("results") or [])

    od = out_dir / "latest_ops_summary.json"
    vd = out_dir / "latest_verdict.json"
    od.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    vd.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
