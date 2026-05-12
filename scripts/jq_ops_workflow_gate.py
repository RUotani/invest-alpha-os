#!/usr/bin/env python3
"""Prepare and validate ops JSON for jq-cache-live / jq-refresh-workflow (no secrets; local-only paths)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _norm_codes_csv(s: str) -> str:
    parts = [p.strip() for p in s.strip().split(",") if p.strip()]
    return ",".join(parts)


def prepare_snapshots(ops_dir: Path) -> None:
    """Remove prior latest_* files so stale verdict cannot gate this run."""

    ops_dir.mkdir(parents=True, exist_ok=True)
    for name in ("latest_ops_summary.json", "latest_verdict.json"):
        p = ops_dir / name
        if p.exists():
            p.unlink()


def _normalize_date_fragment(s: str) -> str:
    return str(s).strip().replace("-", "")


def validate_snapshots(ops_dir: Path, *, date_from: str, date_to: str, codes: str | None) -> tuple[int, str]:
    """Validate summary + verdict for this workflow run."""

    ops_dir.mkdir(parents=True, exist_ok=True)
    verdict_p = ops_dir / "latest_verdict.json"
    summary_p = ops_dir / "latest_ops_summary.json"
    if not verdict_p.is_file():
        return 91, "missing latest_verdict.json after live cache step"
    if not summary_p.is_file():
        return 93, "missing latest_ops_summary.json after live cache step"

    summary = json.loads(summary_p.read_text(encoding="utf-8"))
    verdict = json.loads(verdict_p.read_text(encoding="utf-8"))

    if summary.get("mode") != "jquants_watchlist_cache_live":
        return 94, "ops summary mode mismatch"

    dfs = summary.get("date_from")
    dts = summary.get("date_to")
    if not isinstance(dfs, str) or _normalize_date_fragment(dfs) != _normalize_date_fragment(date_from):
        return 94, "ops summary date_from mismatch"
    if not isinstance(dts, str) or _normalize_date_fragment(dts) != _normalize_date_fragment(date_to):
        return 94, "ops summary date_to mismatch"

    gen = summary.get("generated_at")
    if not isinstance(gen, str) or not gen.strip():
        return 94, "ops summary generated_at missing or invalid"

    if not isinstance(verdict.get("verdict"), str) or not str(verdict["verdict"]).strip():
        return 94, "verdict JSON missing verdict field"

    for k in ("target_count", "failed_codes"):
        if k not in summary:
            return 94, f"ops summary missing {k}"
    fc = summary.get("failed_codes")
    if not isinstance(fc, list):
        return 94, "ops summary failed_codes not a list"
    tc = summary.get("target_count")
    if not isinstance(tc, int) or tc < 0:
        return 94, "ops summary target_count invalid"

    if codes is not None and str(codes).strip():
        normalized_env = _norm_codes_csv(str(codes))
        req = summary.get("codes_requested")
        if not isinstance(req, str) or not req.strip():
            return 94, "ops summary missing codes_requested for CODES run"
        if _norm_codes_csv(req) != normalized_env:
            return 94, "ops summary codes_requested does not match CODES"

    return 0, "ok"


def write_test_fixture(ops_dir: Path, *, fixture: str, date_from: str, date_to: str, codes: str | None) -> None:
    """Emit minimal ops JSON bundles for pytest / gate integration (synthetic-only; not used in prod runs)."""

    ops_dir.mkdir(parents=True, exist_ok=True)
    fixture_w = fixture.strip()

    codes_norm: str | None = None
    if codes is not None and str(codes).strip():
        codes_norm = _norm_codes_csv(str(codes))

    syn_time = "2026-05-09T12:00:00+00:00"

    def base_summary(extra: dict) -> dict:
        s = {
            "schema_version": 1,
            "generated_at": syn_time,
            "mode": "jquants_watchlist_cache_live",
            "skipped_count": 0,
            "live_http_performed": True,
            "raw_response_included": False,
            "date_from": date_from,
            "date_to": date_to,
        }
        s.update(extra)
        if codes_norm is not None:
            s["codes_requested"] = codes_norm
        return s

    if fixture_w == "omit_verdict":
        (ops_dir / "latest_verdict.json").unlink(missing_ok=True)
        ss = base_summary({"target_count": 1, "success_count": 1, "error_count": 0, "cache_written_count": 1, "failed_codes": []})
        (ops_dir / "latest_ops_summary.json").write_text(json.dumps(ss, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return

    if fixture_w == "pass":
        ss = base_summary(
            {"target_count": 2, "success_count": 2, "error_count": 0, "cache_written_count": 2, "failed_codes": []},
        )
        vd = {"schema_version": 1, "generated_at": syn_time, "verdict": "pass", "reason": "fixture pass", "live_http_performed": True}
    elif fixture_w == "partial_success":
        ss = base_summary(
            {"target_count": 3, "success_count": 2, "error_count": 1, "cache_written_count": 2, "failed_codes": ["9999"]},
        )
        vd = {
            "schema_version": 1,
            "generated_at": syn_time,
            "verdict": "partial_success",
            "reason": "fixture partial_success",
            "live_http_performed": True,
        }
    elif fixture_w == "needs_human_review":
        ss = base_summary(
            {"target_count": 1, "success_count": 1, "error_count": 0, "cache_written_count": 1, "failed_codes": []},
        )
        vd = {
            "schema_version": 1,
            "generated_at": syn_time,
            "verdict": "needs_human_review",
            "reason": "fixture human",
            "live_http_performed": True,
        }
    elif fixture_w == "fail":
        ss = base_summary({"target_count": 2, "success_count": 0, "error_count": 2, "cache_written_count": 0, "failed_codes": ["1111", "2222"]})
        vd = {"schema_version": 1, "generated_at": syn_time, "verdict": "fail", "reason": "fixture fail", "live_http_performed": True}
    else:
        raise ValueError(f"unknown fixture kind {fixture!r}")

    (ops_dir / "latest_ops_summary.json").write_text(json.dumps(ss, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ops_dir / "latest_verdict.json").write_text(json.dumps(vd, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="Remove stale latest_ops_* before live.")
    p_prep.add_argument("--ops-dir", type=Path, required=True)

    p_val = sub.add_parser("validate", help="Assert fresh summary/verdict match this FROM/TO/CODES.")
    p_val.add_argument("--ops-dir", type=Path, required=True)
    p_val.add_argument("--from-date", required=True)
    p_val.add_argument("--to-date", required=True)
    p_val.add_argument("--codes", default=None, help="If set (non-empty), require codes_requested match.")

    p_wtf = sub.add_parser("write-test-fixture", help="Synthetic ops JSON bundle for pytest (never for production runs).")
    p_wtf.add_argument("--ops-dir", type=Path, required=True)
    p_wtf.add_argument("--fixture", required=True, help="pass|partial_success|needs_human_review|fail|omit_verdict")
    p_wtf.add_argument("--from-date", required=True)
    p_wtf.add_argument("--to-date", required=True)
    p_wtf.add_argument("--codes", default=None)

    ns = p.parse_args(argv)
    if ns.cmd == "prepare":
        prepare_snapshots(ns.ops_dir)
        return 0
    if ns.cmd == "validate":
        ec, msg = validate_snapshots(
            ns.ops_dir,
            date_from=ns.from_date,
            date_to=ns.to_date,
            codes=ns.codes,
        )
        if ec != 0:
            print(f"jq_ops_workflow_gate validate: {msg}", file=sys.stderr)
        return ec
    if ns.cmd == "write-test-fixture":
        write_test_fixture(
            ns.ops_dir,
            fixture=ns.fixture,
            date_from=ns.from_date,
            date_to=ns.to_date,
            codes=ns.codes,
        )
        return 0
    raise AssertionError(ns.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
