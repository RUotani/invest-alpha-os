"""Sanitized watchlist smoke summaries for local ``outputs/jquants_smoke/`` (Task 9).

No API keys, no raw bodies, no full headers — only CLI-safe numeric / status fields.
Task 9.1 distinguishes **dry_run** / preview-like counts from **error_count**.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.data.adapters.jquants_client import (
    JQUANTS_WATCHLIST_SMOKE_ERROR_STATUSES,
    _parse_v2_daily_bars_date,
)

def _iso_slug_date(raw: str | None) -> str | None:
    if raw is None:
        return None
    wd = _parse_v2_daily_bars_date(raw.strip())
    if wd is None or len(wd) != 8:
        safe = "".join(c for c in raw if c.isalnum() or c in "-_")
        return safe[:48] if safe else "unknown"
    return f"{wd[0:4]}-{wd[4:6]}-{wd[6:8]}"


def build_watchlist_filename_date_slug(
    date_opt: str | None, from_date: str | None, to_date: str | None
) -> str:
    if date_opt:
        return _iso_slug_date(date_opt) or "unknown"
    if from_date and to_date:
        a = _iso_slug_date(from_date) or "from"
        b = _iso_slug_date(to_date) or "to"
        return f"{a}_to_{b}"
    return "unknown"


def sanitize_watchlist_result_rows_for_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in rows:
        row_out: dict[str, Any] = {}
        code = raw.get("code")
        if isinstance(code, str) and code:
            row_out["code"] = code
        elif code is not None:
            row_out["code"] = str(code)

        if "status" in raw:
            row_out["status"] = raw["status"]
        if "row_count" in raw and raw["row_count"] is not None:
            row_out["row_count"] = raw["row_count"]
        if "source_key" in raw and raw["source_key"] is not None:
            row_out["source_key"] = raw["source_key"]
        if "http_status" in raw and raw["http_status"] is not None:
            row_out["http_status"] = raw["http_status"]
        if "error_body_preview" in raw and raw["error_body_preview"] is not None:
            row_out["error_body_preview"] = raw["error_body_preview"]
        out.append(row_out)
    return out


def watchlist_smoke_counts_from_results(
    results: list[Any],
    *,
    cli_top_status: str | None,
) -> dict[str, int]:
    counts = {
        "success_count": 0,
        "error_count": 0,
        "skipped_count": 0,
        "dry_run_count": 0,
        "preview_count": 0,
    }
    for raw in results:
        if not isinstance(raw, dict):
            continue
        st = raw.get("status")
        if st == "skipped_unsupported_code":
            counts["skipped_count"] += 1
        elif st == "success":
            counts["success_count"] += 1
        elif st == "dry_run":
            counts["dry_run_count"] += 1
        elif st == "preview" or (st == "ok" and cli_top_status == "preview"):
            counts["preview_count"] += 1
        elif st in JQUANTS_WATCHLIST_SMOKE_ERROR_STATUSES:
            counts["error_count"] += 1
        else:
            counts["error_count"] += 1
    return counts


def _summary_mode_from_cli_out(cli_out: dict[str, Any]) -> Any:
    st = cli_out.get("status")
    if st == "completed":
        return "live"
    return st


def build_watchlist_smoke_summary_document(cli_out: dict[str, Any]) -> dict[str, Any]:
    """Build on-disk payload from CLI ``out`` blob (already no raw bodies)."""

    results_raw = cli_out.get("results")
    rows = results_raw if isinstance(results_raw, list) else []

    counts = watchlist_smoke_counts_from_results(rows, cli_top_status=cli_out.get("status"))

    sanitized = sanitize_watchlist_result_rows_for_summary(
        [r for r in rows if isinstance(r, dict)]
    )

    return {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": _summary_mode_from_cli_out(cli_out),
        "date": cli_out.get("date"),
        "date_from": cli_out.get("date_from"),
        "date_to": cli_out.get("date_to"),
        "target_count": cli_out.get("target_count"),
        **counts,
        "results": sanitized,
        "raw_response_included": False,
        "api_key_displayed": False,
    }


def save_watchlist_smoke_summary_payload(
    payload: dict[str, Any],
    *,
    date_slug: str,
    limit_display: str,
    output_root: Path | None = None,
) -> tuple[str, str]:
    """Write ``watchlist_bars_<slug>_limit<N|all>.json`` (same slug+limit replaces file) and ``latest.json``; return paths relative to repo root."""

    root = OUTPUTS_DIR if output_root is None else output_root
    dest = root / "jquants_smoke"
    dest.mkdir(parents=True, exist_ok=True)

    fname = f"watchlist_bars_{date_slug}_limit{limit_display}.json"
    path_main = dest / fname
    path_latest = dest / "latest.json"

    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path_main.write_text(serialized, encoding="utf-8")
    path_latest.write_text(serialized, encoding="utf-8")

    def relative_to_repo(p: Path) -> str:
        try:
            return p.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
        except ValueError:
            return p.resolve().as_posix()

    return relative_to_repo(path_main), relative_to_repo(path_latest)