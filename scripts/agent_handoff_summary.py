#!/usr/bin/env python3
"""Build machine-readable and human-readable agent handoff summaries (local outputs/ops; gitignored).

Rejects unknown input keys and blocks ``live_http_performed=true``. Sanitizes string fields."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

_ALLOWED_GEN_EXIT = frozenset(range(256))
_HANDOFF_KEYS: Final[frozenset[str]] = frozenset(
    {
        "pytest_exit_code",
        "pytest_stdout_tail",
        "signals_exit_code",
        "signals_json",
        "daily_momentum_exit_code",
        "investment_os_coverage_exit_code",
        "investment_stdout_tail",
        "post_push_stdout_tail",
        "post_push_classification",
        "git_status_lines",
        "live_http_performed",
    }
)
_ALLOWED_POST_PUSH_CLASS: Final[frozenset[str]] = frozenset({"ok", "skipped_no_gh", "degraded", "unknown"})

_MAX_TAIL_LEN: Final[int] = 8_192


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _no_ctrl(s: str) -> str | None:
    # Allow ASCII space/newline/tab only; reject NUL, C1 controls (except we skip \\r), DEL, unicode whitespace.

    if "\x00" in s:
        return None
    # strip control chars except common newlines preserved in tail excerpts
    out = []
    for ch in s:
        o = ord(ch)
        if ch in ("\n", "\t", " "):
            out.append(ch)
        elif ch == "\r":
            continue
        elif o < 32:
            return None
        elif ch.isspace():
            return None
        elif o == 127:
            return None
        else:
            out.append(ch)
    return "".join(out)


def _sanitize_optional_tail(raw: object) -> str:
    if raw is None:
        return ""
    if not isinstance(raw, str):
        raise ValueError("tail_field_not_string")
    s = raw.strip()
    if len(s) > _MAX_TAIL_LEN:
        s = s[:_MAX_TAIL_LEN] + "\n...[truncated]"
    ok = _no_ctrl(s)
    if ok is None:
        raise ValueError("tail_has_control_chars")
    return ok


def _sanitize_git_status(raw: object) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        inner = raw
    elif isinstance(raw, list):
        inner = "".join(line if isinstance(line, str) else json.dumps(line) for line in raw)
    else:
        raise ValueError("git_status_wrong_type")
    ok_inner = _no_ctrl(inner) if inner.strip() else inner
    if ok_inner is None:
        raise ValueError("git_status_control_chars")
    # Normalise newline for single display field
    return ok_inner.strip().replace("\r\n", "\n").replace("\r", "\n")[: _MAX_TAIL_LEN]


def parse_pytest_count(pytest_stdout_tail: str) -> int | None:
    if not pytest_stdout_tail.strip():
        return None
    lines = pytest_stdout_tail.strip().splitlines()
    last = lines[-1]
    mp = re.search(r"(\d+)\s+passed\b", last)
    if mp:
        return int(mp.group(1))
    mp2 = re.search(r"(\d+)\s+passed\b", pytest_stdout_tail)
    if mp2:
        return int(mp2.group(1))
    return None


def _validate_signals_json(raw: object) -> tuple[int | None, str]:
    """Return (skipped_no_cache or None if absent, canonical json string subset)."""

    if raw is None:
        return None, "null"
    if not isinstance(raw, dict):
        raise ValueError("signals_json_not_object")
    extras = set(raw.keys()) - {"skipped_no_cache"}
    if extras:
        raise ValueError(f"signals_json_extra_keys:{sorted(extras)!r}")
    if "skipped_no_cache" not in raw:
        return None, "{}"
    v = raw["skipped_no_cache"]
    if not isinstance(v, int) or v < 0:
        raise ValueError("signals_json_bad_skipped_no_cache")
    return v, json.dumps({"skipped_no_cache": v}, separators=(",", ":"), sort_keys=True)


def _exit_to_status(ec: object, *, allow: frozenset[int]) -> str:
    if not isinstance(ec, int) or ec not in allow:
        raise ValueError("invalid_exit_code")
    return "passed" if ec == 0 else "failed"


def validate_handoff_payload(raw: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    if not isinstance(raw, dict):
        raise ValueError("payload_not_object")
    unknown = set(raw) - _HANDOFF_KEYS
    if unknown:
        raise ValueError(f"unknown_keys:{sorted(unknown)!r}")
    missing = _HANDOFF_KEYS - set(raw.keys())
    if missing:
        raise ValueError(f"missing_keys:{sorted(missing)!r}")

    pem = raw["pytest_exit_code"]
    sem = raw["signals_exit_code"]
    dem = raw["daily_momentum_exit_code"]
    iem = raw["investment_os_coverage_exit_code"]
    live = raw["live_http_performed"]
    ppc = raw["post_push_classification"]

    if live is True:
        raise ValueError("live_http_not_allowed")
    if live is not False:
        raise ValueError("live_http_must_be_explicit_false")

    if not isinstance(ppc, str) or ppc not in _ALLOWED_POST_PUSH_CLASS:
        raise ValueError("bad_post_push_classification")

    pytest_status = _exit_to_status(pem, allow=_ALLOWED_GEN_EXIT)
    signals_cache_only_status = _exit_to_status(sem, allow=_ALLOWED_GEN_EXIT)
    daily_momentum_check_status = _exit_to_status(dem, allow=_ALLOWED_GEN_EXIT)
    investment_os_coverage_status = _exit_to_status(iem, allow=_ALLOWED_GEN_EXIT)

    pytest_tail_s = _sanitize_optional_tail(raw["pytest_stdout_tail"])
    invest_tail_s = _sanitize_optional_tail(raw["investment_stdout_tail"])
    pp_tail_s = _sanitize_optional_tail(raw["post_push_stdout_tail"])
    gst = _sanitize_git_status(raw["git_status_lines"])

    skipped_parsed: int | None
    skipped_parsed, _ = _validate_signals_json(raw["signals_json"])

    post_push_check_status_map = {"ok": "ok", "skipped_no_gh": "skipped_no_gh", "degraded": "degraded", "unknown": "unknown"}
    post_push_check_status = post_push_check_status_map[ppc]

    pytest_cnt = parse_pytest_count(pytest_tail_s)

    git_status_clean = len(gst.strip()) == 0

    public: dict[str, Any] = {
        "schema_version": 1,
        "pytest_status": pytest_status,
        "pytest_count": pytest_cnt,
        "signals_cache_only_status": signals_cache_only_status,
        "skipped_no_cache": skipped_parsed,
        "daily_momentum_check_status": daily_momentum_check_status,
        "investment_os_coverage_status": investment_os_coverage_status,
        "post_push_check_status": post_push_check_status,
        "git_status_clean": git_status_clean,
        "live_http_performed": False,
        "generated_at": _utc_now_iso(),
    }
    extras: dict[str, str] = {
        "git_status_preview": gst[:2000] if gst else "",
        "investment_stdout_preview": invest_tail_s[:2000],
        "post_push_stdout_preview": pp_tail_s[:2000],
    }
    return public, extras


def merge_logs_to_payload_json(
    *,
    pytest_exit_code: int,
    pytest_stdout_path: Path,
    signals_exit_code: int,
    signals_stdout_path: Path,
    daily_momentum_exit_code: int,
    investment_stdout_path: Path,
    investment_exit_code: int,
    post_push_stdout_path: Path,
    post_push_classification: str,
    git_status_path: Path,
    out_payload_path: Path,
) -> None:
    pytest_tail_s = pytest_stdout_path.read_text(encoding="utf-8", errors="replace").strip()
    pytest_lines = pytest_tail_s.splitlines()
    pytest_tail_trim = ("\n".join(pytest_lines[-48:])).strip() if pytest_lines else ""

    inv_tail = investment_stdout_path.read_text(encoding="utf-8", errors="replace").strip()
    il = inv_tail.splitlines()
    inv_trim = ("\n".join(il[:80])).strip() if il else ""

    pp_txt = post_push_stdout_path.read_text(encoding="utf-8", errors="replace").strip()
    plines = pp_txt.splitlines()
    pp_trim = ("\n".join(plines[-48:])).strip() if plines else ""

    gs = git_status_path.read_text(encoding="utf-8", errors="replace")

    sig_blob: dict[str, Any] | None = None
    if signals_exit_code == 0:
        blob = "".join(signals_stdout_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()).strip()
        if blob.startswith("{"):
            try:
                payload = json.loads(blob)
                if isinstance(payload, dict):
                    sc = payload.get("skipped_no_cache")
                    if sc is None:
                        sig_blob = None
                    elif isinstance(sc, int) and sc >= 0:
                        sig_blob = {"skipped_no_cache": sc}
                    else:
                        sig_blob = None
            except json.JSONDecodeError:
                sig_blob = None

    if post_push_classification not in _ALLOWED_POST_PUSH_CLASS:
        raise ValueError("bad_post_push_classification")

    raw_payload: dict[str, Any] = {
        "pytest_exit_code": pytest_exit_code,
        "pytest_stdout_tail": pytest_tail_trim,
        "signals_exit_code": signals_exit_code,
        "signals_json": sig_blob,
        "daily_momentum_exit_code": daily_momentum_exit_code,
        "investment_os_coverage_exit_code": investment_exit_code,
        "investment_stdout_tail": inv_trim,
        "post_push_stdout_tail": pp_trim,
        "post_push_classification": post_push_classification,
        "git_status_lines": gs,
        "live_http_performed": False,
    }
    validate_handoff_payload(raw_payload)
    out_payload_path.parent.mkdir(parents=True, exist_ok=True)
    out_payload_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def render_markdown(public: dict[str, Any], extras: dict[str, str]) -> str:
    lines = [
        "# Agent final check — handoff summary",
        "",
        f"_Generated:_ `{public['generated_at']}`",
        "",
        "| Check | Status | Detail |",
        "|-------|--------|--------|",
        f"| pytest | `{public['pytest_status']}` | count: `{public.get('pytest_count')}` |",
        f"| signals-cache-only | `{public['signals_cache_only_status']}` | skipped_no_cache: `{public.get('skipped_no_cache')}` |",
        f"| daily-momentum-check | `{public['daily_momentum_check_status']}` | |",
        f"| investment-os-coverage | `{public['investment_os_coverage_status']}` | |",
        f"| post-push-check | `{public['post_push_check_status']}` | |",
        f"| git working tree | `{'clean' if public['git_status_clean'] else 'dirty'}` | |",
        "",
        "**Live HTTP (market / trading):** `false` (this workflow)",
        "",
    ]
    inv_prev = extras.get("investment_stdout_preview") or ""
    if inv_prev.strip():
        lines.extend(["## Coverage doc excerpt", "```markdown", inv_prev.strip()[:2000], "```", ""])
    pp_prev = extras.get("post_push_stdout_preview") or ""
    if pp_prev.strip():
        lines.extend(["## post-push-check excerpt", "```", pp_prev.strip()[:1600], "```", ""])
    gitp = extras.get("git_status_preview") or ""
    if gitp.strip():
        lines.extend(["## Git status (preview)", "```", gitp.strip()[:1600], "```", ""])
    return "\n".join(lines) + "\n"


def cmd_write(from_json_path: Path, ops_dir: Path) -> None:
    raw_txt = from_json_path.read_text(encoding="utf-8")
    raw = json.loads(raw_txt)
    if not isinstance(raw, dict):
        raise SystemExit("input_not_object")
    public, extras = validate_handoff_payload(raw)
    out_json_path = ops_dir / "latest_agent_handoff.json"
    out_md_path = ops_dir / "latest_agent_handoff.md"
    ops_dir.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md_path.write_text(render_markdown(public, extras), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Agent handoff summary writer (strict validation)")
    sub = p.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write", help="Validate input JSON file and emit latest_agent_handoff.*")
    w.add_argument("--from-json", type=Path, required=True)
    w.add_argument(
        "--ops-dir",
        type=Path,
        default=None,
        help="defaults to repo outputs/ops (resolved from cwd if omitted)",
    )
    ml = sub.add_parser("merge-logs", help="Build validated handoff JSON from subprocess log paths")
    ml.add_argument("--pytest-exit-code", type=int, required=True)
    ml.add_argument("--pytest-log", type=Path, required=True)
    ml.add_argument("--signals-exit-code", type=int, required=True)
    ml.add_argument("--signals-log", type=Path, required=True)
    ml.add_argument("--daily-momentum-exit-code", type=int, required=True)
    ml.add_argument("--investment-log", type=Path, required=True)
    ml.add_argument("--investment-exit-code", type=int, required=True)
    ml.add_argument("--post-push-log", type=Path, required=True)
    ml.add_argument("--post-push-classification", required=True)
    ml.add_argument("--git-status-log", type=Path, required=True)
    ml.add_argument("--out-json", type=Path, required=True)
    args = p.parse_args(argv)
    if args.cmd == "write":
        ops_dir = args.ops_dir or (Path(__file__).resolve().parents[1] / "outputs" / "ops")
        cmd_write(Path(args.from_json), ops_dir)
        return 0
    if args.cmd == "merge-logs":
        merge_logs_to_payload_json(
            pytest_exit_code=args.pytest_exit_code,
            pytest_stdout_path=args.pytest_log,
            signals_exit_code=args.signals_exit_code,
            signals_stdout_path=args.signals_log,
            daily_momentum_exit_code=args.daily_momentum_exit_code,
            investment_stdout_path=args.investment_log,
            investment_exit_code=args.investment_exit_code,
            post_push_stdout_path=args.post_push_log,
            post_push_classification=args.post_push_classification,
            git_status_path=args.git_status_log,
            out_payload_path=args.out_json,
        )
        return 0
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
