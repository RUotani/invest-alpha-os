"""v35: Stooq manual OHLCV actual import orchestration, rollback, freshness, readiness."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.data.jquants_daily_bars_cache import (
    jquants_daily_bars_cache_path,
    load_jquants_daily_bars_cache,
)
from invis_alpha_os.reports.chatgpt_trap_analysis import analyze_candidate_traps
from invis_alpha_os.reports.manual_csv_import_execute import build_manual_csv_import_execute
from invis_alpha_os.reports.manual_csv_import_plan import build_manual_csv_import_plan
from invis_alpha_os.reports.manual_data_schema_guard import build_manual_data_schema_validation
from invis_alpha_os.reports.manual_data_import_flow_dry_run import build_manual_data_import_flow_dry_run
from invis_alpha_os.reports.post_contract_ohlcv_structural_analysis_v32 import (
    CONTRACT_DATA_TO,
    _gap_days,
    _load_json,
    _watch_priority_for_candidate,
)

DEFAULT_TARGETS = "5802,6645,285A,5803"
PROVENANCE_SOURCE = "stooq_manual_csv_fallback"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_targets(csv: str) -> list[str]:
    return [p.strip() for p in csv.split(",") if p.strip()]


def _cache_snapshot_meta(ticker: str) -> dict[str, Any]:
    loaded = load_jquants_daily_bars_cache(ticker)
    if not loaded:
        return {
            "ticker": ticker,
            "cache_present": False,
            "latest_date": None,
            "row_count": 0,
            "cache_file": jquants_daily_bars_cache_path(ticker).name,
        }
    bars, meta = loaded
    return {
        "ticker": ticker,
        "cache_present": True,
        "latest_date": str(bars[-1]["date"]) if bars else None,
        "row_count": len(bars),
        "cache_file": jquants_daily_bars_cache_path(ticker).name,
        "cache_source": meta.get("source"),
    }


def build_manual_data_actual_import_rollback_plan(
    *,
    report_date: str,
    targets_csv: str,
    backup_root: Path,
    import_command: str,
) -> tuple[str, dict[str, Any]]:
    targets = _parse_targets(targets_csv)
    backup_dir = backup_root / report_date / _now_iso().replace(":", "").replace("-", "")[:15]
    backup_dir.mkdir(parents=True, exist_ok=True)
    snapshots: list[dict[str, Any]] = []
    for ticker in targets:
        before = _cache_snapshot_meta(ticker)
        src = jquants_daily_bars_cache_path(ticker)
        backup_path: str | None = None
        if src.is_file():
            dest = backup_dir / src.name
            shutil.copy2(src, dest)
            backup_path = str(dest.relative_to(backup_root.parent.parent))
        snapshots.append({**before, "backup_relative": backup_path})
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v35",
        "affected_cache_files": [f"outputs/market_data/jquants_daily_bars/{t}.json" for t in targets],
        "backup_directory_label": str(backup_dir.relative_to(backup_root.parent.parent)),
        "before_by_ticker": snapshots,
        "import_command_recorded": import_command,
        "rollback_note": (
            "Restore from backup_directory by copying each *.json back to "
            "outputs/market_data/jquants_daily_bars/ (manual; not auto-executed)."
        ),
        "raw_cache_contents_printed": False,
    }
    md = "\n".join(
        [
            "# Manual Data Actual Import Rollback Plan",
            "",
            f"- backup_directory: {payload['backup_directory_label']}",
            f"- tickers: {', '.join(targets)}",
            "",
            "| ticker | before_latest | row_count | backup |",
            "|---|---|---:|---|",
        ]
        + [
            f"| {s['ticker']} | {s.get('latest_date') or '-'} | {s.get('row_count', 0)} | "
            f"{'yes' if s.get('backup_relative') else 'no'} |"
            for s in snapshots
        ]
        + ["", "## Rollback", "", f"- {payload['rollback_note']}", ""]
    )
    return md, payload


def build_pre_import_safety_check(
    *,
    csv_path: Path,
    targets_csv: str,
    report_date: str,
    repo_root: Path,
    working_dir: Path,
) -> dict[str, Any]:
    schema = build_manual_data_schema_validation(
        input_path=csv_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    plan = build_manual_csv_import_plan(
        csv_path=csv_path,
        targets_csv=targets_csv,
        report_date=report_date,
    )
    dry = build_manual_data_import_flow_dry_run(
        input_path=csv_path,
        targets_csv=targets_csv,
        report_date=report_date,
        repo_root=repo_root,
        working_dir=working_dir,
        schema_payload=schema.json_payload,
    )
    coverage = {c["ticker"]: c for c in schema.json_payload.get("target_ticker_coverage", [])}
    return {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "file_exists": csv_path.is_file(),
        "schema_valid": schema.json_payload.get("schema_valid"),
        "prohibited_columns_detected": schema.json_payload.get("prohibited_columns_detected"),
        "dry_run_status": dry.json_payload.get("dry_run_status"),
        "rows_newer_than_cache_total": plan.json_payload.get("rows_newer_than_cache_total"),
        "date_max": schema.json_payload.get("date_max"),
        "importable": plan.json_payload.get("importable"),
        "target_coverage": {
            t: coverage.get(t, {}).get("status", "missing") for t in _parse_targets(targets_csv)
        },
        "ready_for_import": (
            schema.json_payload.get("schema_valid")
            and not schema.json_payload.get("prohibited_columns_detected")
            and dry.json_payload.get("dry_run_status") == "pass"
            and int(plan.json_payload.get("rows_newer_than_cache_total") or 0) > 0
        ),
    }


def build_freshness_verification(
    *,
    report_date: str,
    before: list[dict[str, Any]],
    after_execute: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    before_map = {b["ticker"]: b for b in before}
    rows: list[dict[str, Any]] = []
    for sym in after_execute.get("symbol_results") or []:
        ticker = str(sym.get("ticker", ""))
        b = before_map.get(ticker, {})
        loaded = load_jquants_daily_bars_cache(ticker)
        after_latest = None
        after_count = 0
        if loaded:
            bars, meta = loaded
            after_count = len(bars)
            after_latest = str(bars[-1]["date"]) if bars else None
        added = int(sym.get("rows_written") or 0)
        status = str(sym.get("status", "unknown"))
        gap_after = _gap_days(report_date, after_latest)
        rows.append(
            {
                "ticker": ticker,
                "before_latest": b.get("latest_date"),
                "after_latest": after_latest,
                "rows_added": added,
                "after_row_count": after_count,
                "status": status,
                "gap_days_after": gap_after,
                "freshness_status": "fresh" if gap_after is not None and gap_after <= 7 else "stale_improved",
            }
        )
    improved = all(
        r.get("after_latest") and r.get("after_latest") > CONTRACT_DATA_TO for r in rows if r.get("rows_added")
    )
    payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v35",
        "per_ticker": rows,
        "freshness_improvement_detected": improved and any(r.get("rows_added") for r in rows),
        "post_contract_gap_reduced": improved,
        "provenance": PROVENANCE_SOURCE,
    }
    md_lines = [
        "# Manual Import Freshness Verification",
        "",
        f"- freshness_improvement_detected: {payload['freshness_improvement_detected']}",
        "",
        "| ticker | before_latest | after_latest | rows_added | status |",
        "|---|---|---|---:|---|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['ticker']} | {r.get('before_latest') or '-'} | {r.get('after_latest') or '-'} | "
            f"{r.get('rows_added', 0)} | {r.get('status')} |"
        )
    return "\n".join(md_lines), payload


def _candidate_by_ticker(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in context.get("candidates") or []:
        if isinstance(row, dict):
            t = str(row.get("ticker", "")).strip()
            if t:
                out[t] = row
    return out


def build_investment_readiness_after_manual_import(
    *,
    report_date: str,
    reports_latest_dir: Path,
    targets_csv: str = DEFAULT_TARGETS,
) -> tuple[str, dict[str, Any], str, dict[str, Any]]:
    context = _load_json(reports_latest_dir / "chatgpt_invest_context_pack.json")
    candidates = _candidate_by_ticker(context)
    readiness_rows: list[dict[str, Any]] = []
    watch_rows: list[dict[str, Any]] = []
    triggers: list[dict[str, Any]] = []
    for ticker in _parse_targets(targets_csv):
        cand = candidates.get(ticker)
        if not cand:
            readiness_rows.append(
                {
                    "ticker": ticker,
                    "latest_date": None,
                    "freshness_status": "missing_context",
                    "watch_priority": "defer",
                    "confidence": "低",
                    "timing_readiness": "context_missing",
                    "data_provenance": PROVENANCE_SOURCE,
                }
            )
            continue
        latest = str(cand.get("latest_bar_date") or "")
        gap = _gap_days(report_date, latest)
        trap = analyze_candidate_traps(cand)
        watch_pri, watch_reason = _watch_priority_for_candidate(
            ticker=ticker, candidate=cand, trap=trap, gap=gap
        )
        timing = "timing_assessment_possible" if gap is not None and gap <= 7 else "structural_only"
        if gap is not None and gap <= 3:
            timing = "timing_assessment_high_resolution"
        conf = "高" if gap is not None and gap <= 3 else ("中" if gap is not None and gap <= 14 else "低")
        readiness_rows.append(
            {
                "ticker": ticker,
                "latest_date": latest,
                "freshness_status": str(cand.get("freshness_classification", "unknown")),
                "watch_priority": watch_pri,
                "confidence": conf,
                "timing_readiness": timing,
                "watch_priority_reason": watch_reason,
                "data_provenance": PROVENANCE_SOURCE,
                "gap_days": gap,
            }
        )
        watch_rows.append(
            {"ticker": ticker, "watch_priority": watch_pri, "watch_priority_reason": watch_reason}
        )
        triggers.append(
            {
                "ticker": ticker,
                "upside_trigger": list(trap.get("upside_thesis") or [])[:2],
                "downside_trigger": list(trap.get("downside_thesis") or [])[:2],
                "invalidation": list(trap.get("invalidation_conditions") or [])[:3],
            }
        )
    readiness_payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v35",
        "disclaimer": "投資助言ではなく監視優先順位。Stooq manual fallback経由OHLCV。",
        "per_ticker": readiness_rows,
        "provenance": PROVENANCE_SOURCE,
    }
    ordered = sorted(
        watch_rows,
        key=lambda r: {"watch_high": 0, "watch_medium": 1, "watch_low": 2, "defer": 3}.get(
            str(r.get("watch_priority")), 9
        ),
    )
    watch_payload: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v35",
        "priority_order": [r["ticker"] for r in ordered],
        "per_ticker": ordered,
        "key_watch_triggers": triggers,
        "provenance": PROVENANCE_SOURCE,
    }
    r_md = [
        "# Investment Readiness After Manual Import",
        "",
        readiness_payload["disclaimer"],
        "",
        "| ticker | latest_date | watch_priority | confidence | timing_readiness |",
        "|---|---|---|---|---|",
    ]
    for r in readiness_rows:
        r_md.append(
            f"| {r['ticker']} | {r.get('latest_date') or '-'} | {r['watch_priority']} | "
            f"{r['confidence']} | {r['timing_readiness']} |"
        )
    w_md = [
        "# Candidate Watch Priority After Manual Import",
        "",
        f"- priority: {' > '.join(watch_payload['priority_order'])}",
        "",
        "| ticker | watch_priority |",
        "|---|---|",
    ]
    for r in ordered:
        w_md.append(f"| {r['ticker']} | {r['watch_priority']} |")
    return "\n".join(r_md), readiness_payload, "\n".join(w_md), watch_payload


@dataclass(frozen=True)
class ManualImportV35Result:
    pre_import: dict[str, Any]
    rollback_md: str
    rollback_json: dict[str, Any]
    execute_json: dict[str, Any]
    execute_md: str
    freshness_md: str
    freshness_json: dict[str, Any]
    import_result_md: str
    import_result_json: dict[str, Any]
    readiness_md: str
    readiness_json: dict[str, Any]
    watch_md: str
    watch_json: dict[str, Any]


def run_manual_import_v35(
    *,
    report_date: str,
    csv_path: Path,
    targets_csv: str,
    repo_root: Path,
    backup_root: Path,
    working_dir: Path,
    env: dict[str, str],
    execute_import: bool,
) -> ManualImportV35Result:
    import_cmd = (
        "weekly-candidate-brief-manual-data-import-flow --execute-import "
        f"--input-path <dropzone>/manual_jp_bars.csv --targets {targets_csv}"
    )
    pre = build_pre_import_safety_check(
        csv_path=csv_path,
        targets_csv=targets_csv,
        report_date=report_date,
        repo_root=repo_root,
        working_dir=working_dir,
    )
    rb_md, rb_json = build_manual_data_actual_import_rollback_plan(
        report_date=report_date,
        targets_csv=targets_csv,
        backup_root=backup_root,
        import_command=import_cmd,
    )
    before = list(rb_json.get("before_by_ticker") or [])
    exec_result = build_manual_csv_import_execute(
        csv_path=csv_path,
        targets_csv=targets_csv,
        report_date=report_date,
        execute_import=execute_import,
        env=env,
    )
    fresh_md, fresh_json = build_freshness_verification(
        report_date=report_date,
        before=before,
        after_execute=exec_result.json_payload,
    )
    result_payload = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "pack_version": "v35",
        "pre_import_safety": pre,
        "rollback_plan_ref": "manual_data_actual_import_rollback_plan",
        "execute": exec_result.json_payload,
        "freshness": fresh_json,
        "provenance": PROVENANCE_SOURCE,
        "actual_import_executed": exec_result.json_payload.get("actual_import_executed"),
        "cache_write_executed": exec_result.json_payload.get("cache_write_executed"),
    }
    imp_md = "\n".join(
        [
            "# Manual Data Actual Import Result",
            "",
            f"- actual_import_executed: {result_payload['actual_import_executed']}",
            f"- cache_write_executed: {result_payload['cache_write_executed']}",
            f"- overall_status: {exec_result.json_payload.get('overall_status')}",
            f"- rows_newer_than_cache_total: {exec_result.json_payload.get('rows_newer_than_cache_total')}",
            f"- provenance: {PROVENANCE_SOURCE}",
            "",
        ]
    )
    readiness_md, readiness_json, watch_md, watch_json = ("", {}, "", {})
    return ManualImportV35Result(
        pre_import=pre,
        rollback_md=rb_md,
        rollback_json=rb_json,
        execute_json=exec_result.json_payload,
        execute_md=exec_result.markdown_text,
        freshness_md=fresh_md,
        freshness_json=fresh_json,
        import_result_md=imp_md,
        import_result_json=result_payload,
        readiness_md=readiness_md,
        readiness_json=readiness_json,
        watch_md=watch_md,
        watch_json=watch_json,
    )


def write_manual_import_v35_outputs(
    *,
    out_dir: Path,
    report_date: str,
    result: ManualImportV35Result,
) -> dict[str, Path]:
    latest = out_dir / "latest"
    weekly = out_dir / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    pairs = [
        ("manual_data_actual_import_rollback_plan", result.rollback_md, result.rollback_json),
        ("manual_data_actual_import_result", result.import_result_md, result.import_result_json),
        ("manual_import_freshness_verification", result.freshness_md, result.freshness_json),
    ]
    if result.readiness_json:
        pairs.extend(
            [
                ("investment_readiness_after_manual_import", result.readiness_md, result.readiness_json),
                ("candidate_watch_priority_after_manual_import", result.watch_md, result.watch_json),
            ]
        )
    for stem, md, js in pairs:
        for root in (latest, weekly):
            (root / f"{stem}.md").write_text(md, encoding="utf-8")
            (root / f"{stem}.json").write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[f"latest_{stem}_md"] = latest / f"{stem}.md"
    return paths


def sync_manual_import_v35_to_reports_repo(
    *,
    reports_repo_path: Path,
    report_date: str,
    result: ManualImportV35Result,
) -> dict[str, Path]:
    latest = reports_repo_path / "latest"
    weekly = reports_repo_path / "weekly" / "2026" / report_date
    latest.mkdir(parents=True, exist_ok=True)
    weekly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    pairs = [
        ("manual_data_actual_import_rollback_plan", result.rollback_md, result.rollback_json),
        ("manual_data_actual_import_result", result.import_result_md, result.import_result_json),
        ("manual_import_freshness_verification", result.freshness_md, result.freshness_json),
        ("investment_readiness_after_manual_import", result.readiness_md, result.readiness_json),
        ("candidate_watch_priority_after_manual_import", result.watch_md, result.watch_json),
    ]
    for stem, md, js in pairs:
        if not js:
            continue
        for label, root in (("reports_latest", latest), ("reports_weekly", weekly)):
            mp = root / f"{stem}.md"
            jp = root / f"{stem}.json"
            mp.write_text(md, encoding="utf-8")
            jp.write_text(json.dumps(js, ensure_ascii=False, indent=2), encoding="utf-8")
            paths[f"{label}_{stem}_md"] = mp
    return paths
