"""Build ChatGPT context pack from weekly candidate brief artifacts."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.chatgpt_market_regime import build_market_regime_v0
from invis_alpha_os.reports.contract_env_status import (
    append_contract_env_warning,
    build_contract_env_status,
    jp_stale_candidates_without_contract_env,
)
from invis_alpha_os.reports.data_contract_limit import assess_data_contract_limit
from invis_alpha_os.reports.jquants_date_range import contract_dates_from_env
from invis_alpha_os.reports.ohlcv_provider_registry_strategy import build_provider_context_pack_block
from invis_alpha_os.reports.scheduled_report_observability import build_scheduled_report_observability
from invis_alpha_os.reports.weekly_report_schedule_diagnostic import build_weekly_report_schedule_diagnostic
from invis_alpha_os.reports.weekly_report_recovery_runbook import build_weekly_report_recovery_runbook
from invis_alpha_os.reports.weekly_report_workflow_approval_package import (
    build_weekly_report_workflow_approval_package,
)
from invis_alpha_os.reports.weekly_report_local_dryrun_backfill_contract import (
    build_weekly_report_local_dryrun_backfill_contract,
)
from invis_alpha_os.reports.long_run_operator_preflight import build_long_run_operator_preflight_pack
from invis_alpha_os.reports.scheduled_report_assurance_snapshot import build_scheduled_report_assurance_snapshot
from invis_alpha_os.reports.weekly_report_workflow_patch_review_gate import (
    build_weekly_report_workflow_patch_review_gate,
)
from invis_alpha_os.reports.weekly_report_manual_backfill_command_pack import (
    build_weekly_report_manual_backfill_command_pack,
)
from invis_alpha_os.reports.scheduled_report_failure_triage_matrix import (
    build_scheduled_report_failure_triage_matrix,
)
from invis_alpha_os.reports.long_run_development_progress_snapshot import (
    build_long_run_development_progress_snapshot,
)
from invis_alpha_os.reports.weekly_workflow_post_merge_observation_plan import (
    build_weekly_workflow_post_merge_observation_plan,
)
from invis_alpha_os.reports.weekly_candidate_brief_quant_metrics import compute_candidate_quant_metrics


@dataclass(frozen=True)
class ContextPackResult:
    markdown_text: str
    json_payload: dict[str, Any]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _brief_json_path(report_dir: Path) -> Path:
    return report_dir / "weekly_candidate_brief_v0_1.json"


def _read_brief_payload(report_dir: Path) -> dict[str, Any]:
    path = _brief_json_path(report_dir)
    if not path.is_file():
        raise FileNotFoundError(f"weekly_candidate_brief_v0_1.json が見つかりません: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("weekly brief json の形式が不正です")
    return data


def _to_candidate_item(row: dict[str, Any], *, rank: int, report_date: str) -> dict[str, Any]:
    cand = row.get("candidate") or {}
    symbol = str(cand.get("instrument_id", "")).strip()
    market = str(cand.get("market", "")).strip() or "US"
    qm = compute_candidate_quant_metrics(symbol=symbol, market=market, report_date=report_date)
    env_map = dict(os.environ)
    contract_limit = assess_data_contract_limit(
        latest_bar_date=qm.latest_bar_date,
        report_date=report_date,
        contract_to=contract_dates_from_env(env_map).get("data_available_to"),
        freshness_classification=qm.freshness_classification,
    )
    timing_warnings = append_contract_env_warning(
        [],
        env=env_map,
        market=market,
        freshness_classification=qm.freshness_classification,
    )
    return {
        "rank": rank,
        "ticker": symbol,
        "name": str(cand.get("display_name", "")),
        "market": market,
        "classification": str(row.get("brief_type", "")),
        "timing": "要確認",
        "theme": ",".join(str(x) for x in (cand.get("themes") or [])),
        "latest_close": qm.latest_close,
        "latest_bar_date": qm.latest_bar_date,
        "freshness": qm.freshness_label,
        "freshness_classification": qm.freshness_classification,
        "stale_days": qm.stale_days,
        "freshness_reason": qm.freshness_reason,
        "timing_impact": qm.timing_impact,
        "returns": {"d5": qm.ret_5d_pct, "d20": qm.ret_20d_pct, "d60": qm.ret_60d_pct},
        "moving_averages": {
            "ma25": qm.ma_25,
            "ma75": qm.ma_75,
            "ma200": qm.ma_200,
            "dist_ma25_pct": qm.dist_ma_25_pct,
            "dist_ma75_pct": qm.dist_ma_75_pct,
            "dist_ma200_pct": qm.dist_ma_200_pct,
        },
        "range_52w": {
            "high": qm.high_52w,
            "low": qm.low_52w,
            "dist_high_pct": qm.dist_52w_high_pct,
            "dist_low_pct": qm.dist_52w_low_pct,
        },
        "volume": {"latest": qm.latest_volume, "avg20": qm.avg_volume_20d, "ratio20": qm.volume_ratio_20d},
        "momentum_rationale": [str(row.get("reason", ""))],
        "counter_evidence": [str(x) for x in (row.get("counter_evidence") or [])],
        "next_checks": [str(x) for x in (row.get("next_checks") or [])],
        "chatgpt_questions": [
            "この銘柄の上昇シナリオと無効化条件を3つずつ整理してください。",
            "今週の監視ポイントを優先順位付きで示してください。",
        ],
        "missing_data_reasons": [qm.missing_reason] if qm.missing_reason else [],
        "timing_warnings": timing_warnings,
        "sources": [qm.source, "weekly_candidate_brief_v0_1.json"],
        **contract_limit,
    }


def _timing_label_ja(timing: str) -> str:
    labels = {
        "deep_dive": "深掘り",
        "breakout_watch": "ブレイクアウト監視",
        "wait_for_pullback": "押し目待ち",
        "watch_continue": "監視継続",
        "skip": "見送り",
        "data_insufficient": "データ不足",
        "overheated_watch": "過熱監視",
        "data_update_required": "データ更新待ち",
    }
    return labels.get(timing, "要確認")


def _normalize_timing(
    *,
    candidate: dict[str, Any],
    in_skip: bool,
) -> tuple[str, str, list[str]]:
    returns = candidate.get("returns") or {}
    ma = candidate.get("moving_averages") or {}
    classification = str(candidate.get("classification", "")).strip()
    freshness = str(candidate.get("freshness", "")).strip()
    freshness_class = str(candidate.get("freshness_classification", "")).strip()
    missing = candidate.get("missing_data_reasons") or []
    ret20 = returns.get("d20")
    ret60 = returns.get("d60")
    dist25 = ma.get("dist_ma25_pct")
    dist75 = ma.get("dist_ma75_pct")
    try:
        v20 = float(ret20) if ret20 is not None else None
        v60 = float(ret60) if ret60 is not None else None
        d25 = float(dist25) if dist25 is not None else None
        d75 = float(dist75) if dist75 is not None else None
    except (TypeError, ValueError):
        v20, v60, d25, d75 = None, None, None, None

    overheat = bool(
        (v20 is not None and v20 >= 0.3)
        or (v60 is not None and v60 >= 0.6)
        or (d25 is not None and d25 >= 0.15)
        or (d75 is not None and d75 >= 0.2)
    )
    timing_warnings: list[str] = []
    if freshness_class == "data_update_required":
        timing_warnings.append("data_update_required")
    elif freshness_class == "stale":
        timing_warnings.append("stale")
    if missing:
        return "data_insufficient", "定量データに欠損があるためタイミング判定を保留", timing_warnings
    if classification == "top_pick" and in_skip and overheat:
        return "wait_for_pullback", "候補性はあるが短期急伸のため高値追いを回避", timing_warnings
    if classification == "top_pick" and overheat:
        return "overheated_watch", "候補性はあるが過熱警戒で監視優先", timing_warnings
    if "要更新" in freshness:
        return "watch_continue", "データ鮮度が低いため更新後に再評価", timing_warnings
    if classification == "top_pick":
        return "deep_dive", "上位候補として前提条件と無効化条件を優先確認", timing_warnings
    if in_skip:
        return "skip", "反証優位のため見送り", timing_warnings
    return "watch_continue", "継続観測で条件改善を待つ", timing_warnings


def _build_priority_queues(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    queues: dict[str, list[dict[str, str]]] = {
        "deep_dive": [],
        "breakout_watch": [],
        "wait_for_pullback": [],
        "overheated_watch": [],
        "watch_continue": [],
        "data_update_required": [],
        "data_contract_limited": [],
        "data_insufficient": [],
        "skip": [],
    }
    for c in candidates:
        ticker = str(c.get("ticker", "")).strip()
        if not ticker:
            continue
        base_reason = str(c.get("timing_reason", ""))
        entry = {"ticker": ticker, "reason": base_reason}
        timing = str(c.get("timing", "")).strip()
        if timing in queues:
            queues[timing].append(entry)
        warnings = c.get("timing_warnings") or []
        for warning in warnings:
            if warning in queues:
                queues[warning].append({"ticker": ticker, "reason": f"警告: {warning}"})
    return queues


def build_chatgpt_context_pack(*, report_date: str, report_dir: Path) -> ContextPackResult:
    payload = _read_brief_payload(report_dir)
    sections = payload.get("sections") or {}
    top = sections.get("top_picks") or []
    top10 = [_to_candidate_item(row, rank=i + 1, report_date=report_date) for i, row in enumerate(top[:10]) if isinstance(row, dict)]
    avoid = sections.get("avoid") or []
    insuf = sections.get("insufficient") or []

    skip_symbols = {
        str((x.get("candidate") or {}).get("instrument_id", "")).strip()
        for x in avoid
        if isinstance(x, dict)
    }
    for item in top10:
        timing, timing_reason, timing_warnings = _normalize_timing(candidate=item, in_skip=item["ticker"] in skip_symbols)
        item["timing"] = timing
        item["timing_label_ja"] = _timing_label_ja(timing)
        item["timing_reason"] = timing_reason
        item["timing_warnings"] = timing_warnings
        if item.get("data_contract_limited"):
            if "data_contract_limited" not in item["timing_warnings"]:
                item["timing_warnings"].append("data_contract_limited")
        item["quant_data_status"] = "ok" if not item["missing_data_reasons"] else "missing"
    regime = build_market_regime_v0(report_date=report_date)
    queues = _build_priority_queues(top10)
    contract_env = build_contract_env_status()
    jp_env_gap = jp_stale_candidates_without_contract_env(top10)
    provider_block = build_provider_context_pack_block(report_date=report_date)
    weekly_schedule = build_weekly_report_schedule_diagnostic(observed_missing_date="2026-05-30")
    scheduled_observability = build_scheduled_report_observability(as_of_date=report_date)
    recovery_runbook = build_weekly_report_recovery_runbook(missed_report_date="2026-05-30")
    workflow_approval = build_weekly_report_workflow_approval_package(report_date=report_date)
    local_dryrun_contract = build_weekly_report_local_dryrun_backfill_contract(report_date=report_date)
    long_run_preflight = build_long_run_operator_preflight_pack(report_date=report_date)
    assurance_snapshot = build_scheduled_report_assurance_snapshot(report_date=report_date)
    workflow_patch_review_gate = build_weekly_report_workflow_patch_review_gate(report_date=report_date)
    manual_backfill_command_pack = build_weekly_report_manual_backfill_command_pack(report_date=report_date)
    failure_triage = build_scheduled_report_failure_triage_matrix(report_date=report_date)
    progress_snapshot = build_long_run_development_progress_snapshot(report_date=report_date)
    workflow_observation_plan = build_weekly_workflow_post_merge_observation_plan(report_date=report_date)

    out_json: dict[str, Any] = {
        "report_date": report_date,
        "generated_at": _now_iso(),
        "source": "weekly_candidate_brief",
        "contract_env": contract_env,
        "language": "ja",
        "disclaimer": "投資助言ではなく、観測・検証用です",
        "market_regime": regime,
        "summary": {
            "a_candidates": [c["ticker"] for c in top10[:3]],
            "b_candidates": [c["ticker"] for c in top10[3:6]],
            "watch_candidates": [c["ticker"] for c in top10[6:10]],
            "skip_candidates": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in avoid[:5] if isinstance(x, dict)],
            "data_insufficient": [str((x.get("candidate") or {}).get("instrument_id", "")) for x in insuf[:5] if isinstance(x, dict)],
            "main_themes": [str(x.get("reason", "")) for x in top[:3] if isinstance(x, dict)],
            "main_risks": [str((x.get("counter_evidence") or [""])[0]) for x in top[:3] if isinstance(x, dict)],
        },
        "candidates": top10,
        "research_queue": {
            "deep_dive": queues["deep_dive"],
            "breakout_watch": queues["breakout_watch"],
            "wait_for_pullback": queues["wait_for_pullback"],
            "overheated_watch": queues["overheated_watch"],
            "watch_continue": queues["watch_continue"],
            "data_update_required": queues["data_update_required"],
            "data_contract_limited": queues["data_contract_limited"],
            "data_insufficient": queues["data_insufficient"],
            "skip": queues["skip"],
        },
        "provider_registry_status": provider_block["provider_registry_status"],
        "provider_selection_policy": provider_block["provider_selection_policy"],
        "latest_ohlcv_provider_by_ticker": provider_block["latest_ohlcv_provider_by_ticker"],
        "fallback_required_tickers": provider_block["fallback_required_tickers"],
        "approval_gate_status": provider_block["approval_gate_status"],
        "provider_approval_package_status": provider_block["provider_approval_package_status"],
        "provider_safe_execution_harness_status": provider_block["provider_safe_execution_harness_status"],
        "provider_approved_execution_runbook_status": provider_block["provider_approved_execution_runbook_status"],
        "provider_execution_approval_request_status": provider_block["provider_execution_approval_request_status"],
        "us_ohlcv_provider_selection_status": provider_block["us_ohlcv_provider_selection_status"],
        "us_provider_current_evidence_status": provider_block["us_provider_current_evidence_status"],
        "us_ohlcv_pilot_approval_bundle_status": provider_block["us_ohlcv_pilot_approval_bundle_status"],
        "tiingo_current_docs_recheck_status": provider_block["tiingo_current_docs_recheck_status"],
        "tiingo_manual_signoff_ledger_status": provider_block["tiingo_manual_signoff_ledger_status"],
        "tiingo_live_fetch_result_review_status": provider_block["tiingo_live_fetch_result_review_status"],
        "cross_provider_validation_runbook_status": provider_block["cross_provider_validation_runbook_status"],
        "cross_provider_validation_result_review_status": provider_block[
            "cross_provider_validation_result_review_status"
        ],
        "cache_write_readiness_gate_status": provider_block["cache_write_readiness_gate_status"],
        "cache_write_operator_signoff_sheet_status": provider_block["cache_write_operator_signoff_sheet_status"],
        "cache_path_preflight_approval_package_status": provider_block[
            "cache_path_preflight_approval_package_status"
        ],
        "cache_purge_inventory_dryrun_contract_status": provider_block[
            "cache_purge_inventory_dryrun_contract_status"
        ],
        "cache_write_pilot_approval_packet_status": provider_block["cache_write_pilot_approval_packet_status"],
        "cache_write_pilot_result_review_gate_status": provider_block[
            "cache_write_pilot_result_review_gate_status"
        ],
        "actual_import_readiness_boundary_status": provider_block["actual_import_readiness_boundary_status"],
        "weekly_report_schedule_diagnostic_status": {
            "diagnostic_exists": True,
            "user_observed_issue": weekly_schedule["user_observed_issue"],
            "root_cause_found": weekly_schedule["root_cause_found"],
            "github_weekly_schedule_found": weekly_schedule["detected_scheduler_wiring"]["github_actions"][
                "github_weekly_schedule_found"
            ],
            "launchd_template_exists": weekly_schedule["detected_scheduler_wiring"]["launchd_template"]["exists"],
            "workflow_change_required": weekly_schedule["workflow_change_required"],
            "next_scheduled_report_confidence": weekly_schedule["next_scheduled_report_confidence"],
            "workflow_files_modified": weekly_schedule["safety_summary"]["workflow_files_modified"],
        },
        "scheduled_report_observability_status": {
            "sentinel_exists": True,
            "expected_date": scheduled_observability["last_expected_occurrence"]["expected_date"],
            "missing_report_verdict": scheduled_observability["missing_report_verdict"],
            "github_actions_cron_utc": scheduled_observability["expected_schedule"]["github_actions_cron_utc"],
            "raw_market_data_read": scheduled_observability["evidence_inputs"]["raw_market_data_read"],
            "workflow_files_modified": scheduled_observability["safety_summary"]["workflow_files_modified"],
            "gmail_send_executed": scheduled_observability["safety_summary"]["gmail_send_executed"],
        },
        "weekly_report_recovery_runbook_status": {
            "runbook_exists": True,
            "missed_report_date": recovery_runbook["missed_report_context"]["missed_report_date"],
            "this_pack_approves_backfill_execution": recovery_runbook["backfill_approval_boundary"][
                "this_pack_approves_backfill_execution"
            ],
            "manual_backfill_requires_human_choice": recovery_runbook["backfill_approval_boundary"][
                "manual_backfill_requires_human_choice"
            ],
            "workflow_files_modified": recovery_runbook["safety_summary"]["workflow_files_modified"],
            "gmail_send_executed": recovery_runbook["safety_summary"]["gmail_send_executed"],
            "provider_live_access_executed": recovery_runbook["safety_summary"]["provider_live_access_executed"],
        },
        "weekly_report_workflow_approval_package_status": {
            "package_exists": True,
            "readiness_verdict": workflow_approval["readiness_verdict"],
            "workflow_patch_required": workflow_approval["current_scheduler_assessment"]["workflow_patch_required"],
            "wrong_cron_detected": workflow_approval["current_scheduler_assessment"]["wrong_cron_detected"],
            "github_actions_cron_utc": workflow_approval["target_schedule"]["github_actions_cron_utc"],
            "workflow_files_modified": workflow_approval["safety_summary"]["workflow_files_modified"],
            "next_task": workflow_approval["context_summary"]["next_task"],
        },
        "weekly_report_local_dryrun_backfill_contract_status": {
            "contract_exists": True,
            "readiness_verdict": local_dryrun_contract["readiness_verdict"],
            "missed_report_date": local_dryrun_contract["missed_report_date"],
            "local_dryrun_execution_approved_by_this_pack": local_dryrun_contract["scope"][
                "local_dryrun_execution_approved_by_this_pack"
            ],
            "manual_backfill_execution_approved_by_this_pack": local_dryrun_contract["scope"][
                "manual_backfill_execution_approved_by_this_pack"
            ],
            "raw_ohlcv_persistence_executed": local_dryrun_contract["safety_summary"][
                "raw_ohlcv_persistence_executed"
            ],
            "workflow_files_modified": local_dryrun_contract["safety_summary"]["workflow_files_modified"],
            "next_task": local_dryrun_contract["next_task"],
        },
        "long_run_operator_preflight_sleep_guard_status": {
            "pack_exists": True,
            "readiness_verdict": long_run_preflight["readiness_verdict"],
            "recommended_command": long_run_preflight["sleep_prevention"]["recommended_command"],
            "future_long_run_max_instructions_include_sleep_guard": long_run_preflight[
                "handoff_inclusion_contract"
            ]["future_long_run_max_instructions_include_sleep_guard"],
            "future_cursor_handoffs_include_sleep_guard": long_run_preflight["handoff_inclusion_contract"][
                "future_cursor_handoffs_include_sleep_guard"
            ],
            "macos_system_settings_changed": long_run_preflight["safety_summary"]["macos_system_settings_changed"],
            "workflow_files_modified": long_run_preflight["safety_summary"]["workflow_files_modified"],
            "next_task": long_run_preflight["next_task"],
        },
        "scheduled_report_assurance_snapshot_status": {
            "snapshot_exists": True,
            "readiness_verdict": assurance_snapshot["readiness_verdict"],
            "next_run_date_jst": assurance_snapshot["next_run_target"]["next_run_date_jst"],
            "next_run_local_time": assurance_snapshot["next_run_target"]["next_run_local_time"],
            "github_actions_cron_utc": assurance_snapshot["next_run_target"]["github_actions_cron_utc"],
            "next_scheduled_report_confidence": assurance_snapshot["next_scheduled_report_confidence"],
            "workflow_files_modified": assurance_snapshot["safety_summary"]["workflow_files_modified"],
            "gmail_send_executed": assurance_snapshot["safety_summary"]["gmail_send_executed"],
        },
        "weekly_report_workflow_patch_review_gate_status": {
            "gate_exists": True,
            "readiness_verdict": workflow_patch_review_gate["readiness_verdict"],
            "workflow_patch_required": workflow_patch_review_gate["approval_gate"]["workflow_patch_required"],
            "human_approval_required": workflow_patch_review_gate["approval_gate"]["human_approval_required"],
            "utc_cron_expression": workflow_patch_review_gate["schedule"]["utc_cron_expression"],
            "corresponding_jst_schedule": workflow_patch_review_gate["schedule"]["corresponding_jst_schedule"],
            "manual_workflow_dispatch_required": workflow_patch_review_gate["schedule"][
                "manual_workflow_dispatch_required"
            ],
            "workflow_files_modified": workflow_patch_review_gate["safety_summary"]["workflow_files_modified"],
            "next_task": workflow_patch_review_gate["next_task"],
        },
        "weekly_report_manual_backfill_command_pack_status": {
            "pack_exists": True,
            "readiness_verdict": manual_backfill_command_pack["readiness_verdict"],
            "missed_report_date": manual_backfill_command_pack["missed_report_date"],
            "timezone": manual_backfill_command_pack["timezone"],
            "manual_backfill_execution_approved_by_this_pack": manual_backfill_command_pack["dry_run_boundary"][
                "manual_backfill_execution_approved_by_this_pack"
            ],
            "raw_data_outputs_allowed": manual_backfill_command_pack["expected_output_schema"][
                "raw_data_outputs_allowed"
            ],
            "workflow_files_modified": manual_backfill_command_pack["safety_summary"]["workflow_files_modified"],
            "gmail_send_executed": manual_backfill_command_pack["safety_summary"]["gmail_send_executed"],
            "next_task": manual_backfill_command_pack["next_task"],
        },
        "scheduled_report_failure_triage_matrix_status": {
            "matrix_exists": True,
            "readiness_verdict": failure_triage["readiness_verdict"],
            "failure_classes": [row["failure_class"] for row in failure_triage["triage_matrix"]],
            "utc_cron_expression": failure_triage["expected_schedule"]["utc_cron_expression"],
            "secret_values_may_be_displayed": failure_triage["evidence_boundaries"][
                "secret_values_may_be_displayed"
            ],
            "workflow_files_modified": failure_triage["safety_summary"]["workflow_files_modified"],
            "next_task": failure_triage["next_task"],
        },
        "long_run_development_progress_snapshot_status": {
            "snapshot_exists": True,
            "readiness_verdict": progress_snapshot["readiness_verdict"],
            "single_overall_percent_allowed": progress_snapshot["progress_policy"][
                "single_overall_percent_allowed"
            ],
            "domains": [row["domain"] for row in progress_snapshot["domain_progress"]],
            "hard_gate_status": progress_snapshot["hard_gate_status"],
            "workflow_files_modified": progress_snapshot["safety_summary"]["workflow_files_modified"],
        },
        "weekly_workflow_post_merge_observation_plan_status": {
            "plan_exists": True,
            "readiness_verdict": workflow_observation_plan["readiness_verdict"],
            "next_run_date_jst": workflow_observation_plan["next_run_target"]["next_run_date_jst"],
            "next_run_local_time": workflow_observation_plan["next_run_target"]["next_run_local_time"],
            "github_actions_cron_utc": workflow_observation_plan["next_run_target"]["github_actions_cron_utc"],
            "workflow_exists": workflow_observation_plan["workflow_source_status"]["workflow_exists"],
            "expected_cron_found": workflow_observation_plan["workflow_source_status"]["expected_cron_found"],
            "manual_workflow_dispatch_executed": workflow_observation_plan["safety_summary"][
                "manual_workflow_dispatch_executed"
            ],
            "workflow_files_modified": workflow_observation_plan["safety_summary"]["workflow_files_modified"],
            "next_task": workflow_observation_plan["next_task"],
        },
        "manual_csv_is_fallback_not_primary": provider_block["manual_csv_is_fallback_not_primary"],
        "week_over_week_changes": {
            "new": ["未実装"],
            "up": ["未実装"],
            "down": ["未実装"],
            "removed": ["未実装"],
            "continued": ["未実装"],
        },
    }

    md_lines: list[str] = [
        "# ChatGPT投資対話用Context Pack",
        "",
        "## 0. メタ情報",
        f"- レポート日: {report_date}",
        f"- 生成日時: {out_json['generated_at']}",
        "- データ鮮度: 候補ごとの定量スナップショットを参照",
        "- 対象市場: JP / US / ETF",
        "- 生成元: weekly_candidate_brief_v0_1.json",
        "- 注意書き: 投資助言ではなく、観測・検証用です",
        f"- jquants_contract_env_loaded: {str(contract_env['jquants_contract_env_loaded']).lower()}",
        f"- contract_env_not_loaded: {str(contract_env['contract_env_not_loaded']).lower()}",
    ]
    if jp_env_gap:
        md_lines.append(f"- contract_env_gap_tickers: {', '.join(jp_env_gap)}")
    md_lines.extend(
        [
        "",
        "## 1. 今週の結論",
        f"- A候補: {', '.join(out_json['summary']['a_candidates']) or 'なし'}",
        f"- B候補: {', '.join(out_json['summary']['b_candidates']) or 'なし'}",
        f"- 見送り候補: {', '.join(out_json['summary']['skip_candidates']) or 'なし'}",
        f"- データ不足候補: {', '.join(out_json['summary']['data_insufficient']) or 'なし'}",
        "- 今週の主要テーマ: 候補理由を参照",
        "- 最大の注意点: stale/データ不足理由を優先確認",
        "",
        "## 2. 市場レジーム",
        f"- レジーム判定: {regime['label']}",
        f"- 注意点: {', '.join(regime.get('notes') or [])}",
        "- 根拠:",
        *[
            f"  - {px['ticker']}: ret20={px['ret20']}, ret60={px['ret60']}, ma75={px['dist_ma75_pct']}, ma200={px['dist_ma200_pct']}, fresh={px['freshness_classification']}"
            for px in regime.get("proxies", [])
        ],
        "",
        "## 3. 注目候補Top10",
        ]
    )
    for c in top10:
        md_lines.extend(
            [
                f"### {c['rank']}. {c['ticker']} — {c['name']}",
                f"- 候補分類: {c['classification']}",
                f"- タイミング分類: {c['timing']}（{c['timing_label_ja']}）",
                f"- タイミング理由: {c['timing_reason']}",
                f"- 直近終値: {c['latest_close']}",
                f"- 直近データ日: {c['latest_bar_date']}",
                f"- データ鮮度: {c['freshness']}",
                f"- 定量データ状態: {c['quant_data_status']}",
                f"- 欠損理由: {', '.join(c['missing_data_reasons']) or 'なし'}",
                f"- データ鮮度分類: {c.get('freshness_classification')}",
                f"- stale日数: {c.get('stale_days')}",
                f"- stale理由: {c.get('freshness_reason')}",
                f"- タイミングへの影響: {c.get('timing_impact')}",
                f"- タイミング警告: {', '.join(c.get('timing_warnings') or []) or 'なし'}",
                f"- data_contract_limited: {str(c.get('data_contract_limited', False)).lower()}",
                f"- provider_plan_upgrade_required: {str(c.get('provider_plan_upgrade_required', False)).lower()}",
                f"- alternative_provider_required: {str(c.get('alternative_provider_required', False)).lower()}",
                f"- 5D/20D/60D騰落率: {c['returns']['d5']}, {c['returns']['d20']}, {c['returns']['d60']}",
                f"- 25D/75D/200D移動平均線との乖離: {c['moving_averages']['dist_ma25_pct']}, {c['moving_averages']['dist_ma75_pct']}, {c['moving_averages']['dist_ma200_pct']}",
                f"- 52週高値/安値との距離: {c['range_52w']['dist_high_pct']}, {c['range_52w']['dist_low_pct']}",
                f"- 出来高倍率: {c['volume']['ratio20']}",
                f"- モメンタム根拠: {', '.join(c['momentum_rationale']) or 'なし'}",
                f"- 反証・下落リスク: {', '.join(c['counter_evidence']) or 'なし'}",
                f"- 次に確認すること: {', '.join(c['next_checks']) or 'なし'}",
                f"- このチャットで議論したい問い: {', '.join(c['chatgpt_questions'])}",
                "",
            ]
        )
    md_lines.extend(
        [
            "## 4. 深掘り優先キュー",
            "### 深掘り",
            *[
                f"- {row['ticker']} ({row['reason']})"
                for row in out_json["research_queue"]["deep_dive"][:5]
            ],
            "",
            "### 過熱監視",
            *[
                f"- {row['ticker']} ({row['reason']})"
                for row in out_json["research_queue"]["overheated_watch"][:5]
            ],
            "",
            "### 押し目待ち",
            *[
                f"- {row['ticker']} ({row['reason']})"
                for row in out_json["research_queue"]["wait_for_pullback"][:5]
            ],
            "",
            "### 監視継続",
            *[
                f"- {row['ticker']} ({row['reason']})"
                for row in out_json["research_queue"]["watch_continue"][:5]
            ],
            "",
            "### データ更新待ち",
            *[
                f"- {row['ticker']} ({row['reason']})"
                for row in out_json["research_queue"]["data_update_required"][:5]
            ],
            "",
            "### データ不足",
            *[
                f"- {row['ticker']} ({row['reason']})"
                for row in out_json["research_queue"]["data_insufficient"][:5]
            ],
            "",
            "### 見送り",
            *[
                f"- {row['ticker']} ({row['reason']})"
                for row in out_json["research_queue"]["skip"][:5]
            ],
            "",
            "## 5. 前週からの変化",
            "- 未実装（次PR候補）",
            "",
            "## 6. 欠損・注意データ",
            "- stale: 候補ごとのデータ鮮度を参照",
            "- cache不足: missing_data_reasons を参照",
            "",
            "## 6.5. OHLCV Provider Policy",
            f"- provider_registry_status: {provider_block['provider_registry_status']}",
            f"- manual_csv_is_fallback_not_primary: {str(provider_block['manual_csv_is_fallback_not_primary']).lower()}",
            "- approval_gate_status: live_http=false, cache_write=false",
            f"- provider_approval_package_available: {str(provider_block['provider_approval_package_status']['available']).lower()}",
            f"- provider_safe_execution_harness_available: {str(provider_block['provider_safe_execution_harness_status']['available']).lower()}",
            f"- provider_safe_execution_current_verdict: {provider_block['provider_safe_execution_harness_status']['current_verdict']}",
            f"- provider_approved_execution_runbook_available: {str(provider_block['provider_approved_execution_runbook_status']['available']).lower()}",
            f"- provider_approved_execution_runbook_phase: {provider_block['provider_approved_execution_runbook_status']['current_phase']}",
            f"- provider_execution_approval_request_available: {str(provider_block['provider_execution_approval_request_status']['available']).lower()}",
            f"- provider_execution_approval_request_phase: {provider_block['provider_execution_approval_request_status']['current_phase']}",
            f"- us_ohlcv_provider_selected: {str(provider_block['us_ohlcv_provider_selection_status']['provider_selected']).lower()}",
            f"- us_ohlcv_selection_matrix_exists: {str(provider_block['us_ohlcv_provider_selection_status']['selection_matrix_exists']).lower()}",
            f"- us_ohlcv_recommended_first_pilot_provider: {provider_block['us_ohlcv_provider_selection_status']['recommended_first_pilot_provider']}",
            f"- us_ohlcv_recommended_free_fallback: {provider_block['us_ohlcv_provider_selection_status']['recommended_free_fallback']}",
            f"- us_provider_current_evidence_pack_exists: {str(provider_block['us_provider_current_evidence_status']['current_evidence_pack_exists']).lower()}",
            f"- us_provider_current_evidence_confidence: {provider_block['us_provider_current_evidence_status']['evidence_confidence']}",
            f"- us_provider_current_evidence_needs_recheck: {str(provider_block['us_provider_current_evidence_status']['needs_current_recheck']).lower()}",
            f"- us_ohlcv_pilot_approval_bundle_exists: {str(provider_block['us_ohlcv_pilot_approval_bundle_status']['pilot_approval_bundle_exists']).lower()}",
            f"- us_ohlcv_pilot_provider: {provider_block['us_ohlcv_pilot_approval_bundle_status']['recommended_first_pilot_provider']}",
            f"- us_ohlcv_pilot_scenario: {provider_block['us_ohlcv_pilot_approval_bundle_status']['scenario']}",
            f"- us_ohlcv_pilot_approval_phrase_required: {provider_block['us_ohlcv_pilot_approval_bundle_status']['approval_phrase_required']}",
            f"- us_ohlcv_pilot_next_step_requires_explicit_human_approval: {str(provider_block['us_ohlcv_pilot_approval_bundle_status']['next_step_requires_explicit_human_approval']).lower()}",
            f"- tiingo_current_docs_recheck_pack_exists: {str(provider_block['tiingo_current_docs_recheck_status']['recheck_pack_exists']).lower()}",
            f"- tiingo_manual_recheck_required_before_live_fetch: {str(provider_block['tiingo_current_docs_recheck_status']['manual_recheck_required_before_live_fetch']).lower()}",
            f"- tiingo_pricing_terms_cache_adjustment_rate_limit_signoff_required: {str(provider_block['tiingo_current_docs_recheck_status']['pricing_terms_cache_adjustment_rate_limit_signoff_required']).lower()}",
            f"- tiingo_pilot_approved: {str(provider_block['tiingo_current_docs_recheck_status']['pilot_approved']).lower()}",
            f"- tiingo_recheck_next_action: {provider_block['tiingo_current_docs_recheck_status']['next_action']}",
            f"- tiingo_manual_signoff_ledger_exists: {str(provider_block['tiingo_manual_signoff_ledger_status']['manual_signoff_ledger_exists']).lower()}",
            f"- tiingo_manual_signoff_all_items_default_unreviewed: {str(provider_block['tiingo_manual_signoff_ledger_status']['all_items_default_unreviewed']).lower()}",
            f"- tiingo_manual_signoff_primary_blocker: {provider_block['tiingo_manual_signoff_ledger_status']['primary_blocker']}",
            f"- tiingo_manual_signoff_next_action: {provider_block['tiingo_manual_signoff_ledger_status']['next_action']}",
            f"- tiingo_v63b_result_review_pack_exists: {str(provider_block['tiingo_live_fetch_result_review_status']['result_review_pack_exists']).lower()}",
            f"- tiingo_v63b_result_status: {provider_block['tiingo_live_fetch_result_review_status']['v63b_result_status']}",
            f"- tiingo_v63b_symbols_success: {provider_block['tiingo_live_fetch_result_review_status']['symbols_success']}/{provider_block['tiingo_live_fetch_result_review_status']['symbols_total']}",
            f"- tiingo_v63b_base_fields_all_present: {str(provider_block['tiingo_live_fetch_result_review_status']['base_fields_all_present']).lower()}",
            f"- tiingo_v63b_adjusted_fields_all_present: {str(provider_block['tiingo_live_fetch_result_review_status']['adjusted_fields_all_present']).lower()}",
            f"- tiingo_v63b_raw_data_persisted: {str(provider_block['tiingo_live_fetch_result_review_status']['raw_data_persisted']).lower()}",
            f"- tiingo_next_recommended_task: {provider_block['tiingo_live_fetch_result_review_status']['next_recommended_task']}",
            f"- tiingo_cache_write_readiness: {provider_block['tiingo_live_fetch_result_review_status']['cache_write_readiness']}",
            f"- cross_provider_validation_runbook_exists: {str(provider_block['cross_provider_validation_runbook_status']['runbook_pack_exists']).lower()}",
            f"- cross_provider_validation_package_status: {provider_block['cross_provider_validation_runbook_status']['package_status']}",
            f"- cross_provider_validation_operation: {provider_block['cross_provider_validation_runbook_status']['operation']}",
            f"- cross_provider_validation_providers: {', '.join(provider_block['cross_provider_validation_runbook_status']['providers'])}",
            f"- cross_provider_validation_optional_providers: {', '.join(provider_block['cross_provider_validation_runbook_status']['optional_providers'])}",
            f"- cross_provider_validation_approval_phrase_issued: {str(provider_block['cross_provider_validation_runbook_status']['approval_phrase_issued']).lower()}",
            f"- cross_provider_validation_requires_explicit_approval: {str(provider_block['cross_provider_validation_runbook_status']['separate_explicit_approval_required']).lower()}",
            f"- cross_provider_validation_raw_data_persistence_allowed: {str(provider_block['cross_provider_validation_runbook_status']['raw_data_persistence_allowed']).lower()}",
            f"- cross_provider_validation_cache_write_approved: {str(provider_block['cross_provider_validation_runbook_status']['cache_write_approved']).lower()}",
            f"- cross_provider_validation_actual_import_approved: {str(provider_block['cross_provider_validation_runbook_status']['actual_import_approved']).lower()}",
            f"- cross_provider_v65_result_review_exists: {str(provider_block['cross_provider_validation_result_review_status']['result_review_pack_exists']).lower()}",
            f"- cross_provider_v65_verdict: {provider_block['cross_provider_validation_result_review_status']['v65_verdict']}",
            f"- cross_provider_v65_required_provider_symbols_success: {provider_block['cross_provider_validation_result_review_status']['required_provider_symbols_success']}",
            f"- cross_provider_tiingo_yahoo_adjusted_close_consistency: {provider_block['cross_provider_validation_result_review_status']['tiingo_yahoo_adjusted_close_consistency']}",
            f"- cross_provider_stooq_adjusted_comparison_suitability: {provider_block['cross_provider_validation_result_review_status']['stooq_adjusted_comparison_suitability']}",
            f"- cross_provider_nvda_avgo_warning_interpretation: {provider_block['cross_provider_validation_result_review_status']['nvda_avgo_warning_interpretation']}",
            f"- cross_provider_tiingo_adjusted_series_confidence: {provider_block['cross_provider_validation_result_review_status']['tiingo_adjusted_series_confidence']}",
            f"- cross_provider_v66_next_task: {provider_block['cross_provider_validation_result_review_status']['next_recommended_task']}",
            f"- cache_write_readiness_gate_exists: {str(provider_block['cache_write_readiness_gate_status']['gate_exists']).lower()}",
            f"- cache_write_readiness_gate_status: {provider_block['cache_write_readiness_gate_status']['gate_status']}",
            f"- cache_write_signoff16_status: {provider_block['cache_write_readiness_gate_status']['signoff16_status']}",
            f"- cache_write_gate_cache_write_approved: {str(provider_block['cache_write_readiness_gate_status']['cache_write_approved']).lower()}",
            f"- cache_write_gate_actual_import_approved: {str(provider_block['cache_write_readiness_gate_status']['actual_import_approved']).lower()}",
            f"- cache_write_gate_approval_phrase_issued: {str(provider_block['cache_write_readiness_gate_status']['approval_phrase_issued']).lower()}",
            f"- cache_write_gate_cache_location: {provider_block['cache_write_readiness_gate_status']['cache_location']}",
            f"- cache_write_gate_raw_data_git_allowed: {str(provider_block['cache_write_readiness_gate_status']['raw_data_git_allowed']).lower()}",
            f"- cache_write_gate_raw_data_reports_private_allowed: {str(provider_block['cache_write_readiness_gate_status']['raw_data_reports_private_allowed']).lower()}",
            f"- cache_write_gate_future_pilot_subset: {', '.join(provider_block['cache_write_readiness_gate_status']['future_cache_write_pilot_subset'])}",
            f"- cache_write_operator_signoff_sheet_exists: {str(provider_block['cache_write_operator_signoff_sheet_status']['sheet_exists']).lower()}",
            f"- cache_write_operator_signoff_status: {provider_block['cache_write_operator_signoff_sheet_status']['operator_signoff_status']}",
            f"- cache_write_operator_overall_readiness: {provider_block['cache_write_operator_signoff_sheet_status']['overall_readiness']}",
            f"- cache_write_operator_cache_path_proposed: {provider_block['cache_write_operator_signoff_sheet_status']['cache_path_proposed']}",
            f"- cache_write_operator_cache_write_approval_status: {provider_block['cache_write_operator_signoff_sheet_status']['cache_write_approval_status']}",
            f"- cache_write_operator_actual_import_approval_status: {provider_block['cache_write_operator_signoff_sheet_status']['actual_import_approval_status']}",
            f"- cache_write_operator_approval_phrase_issued: {str(provider_block['cache_write_operator_signoff_sheet_status']['approval_phrase_issued']).lower()}",
            f"- cache_path_preflight_package_exists: {str(provider_block['cache_path_preflight_approval_package_status']['package_exists']).lower()}",
            f"- cache_path_preflight_verdict: {provider_block['cache_path_preflight_approval_package_status']['preflight_verdict']}",
            f"- cache_path_preflight_candidate_path: {provider_block['cache_path_preflight_approval_package_status']['candidate_cache_path']}",
            f"- cache_path_preflight_filesystem_probe_performed: {str(provider_block['cache_path_preflight_approval_package_status']['filesystem_probe_performed']).lower()}",
            f"- cache_path_preflight_directory_created: {str(provider_block['cache_path_preflight_approval_package_status']['directory_created']).lower()}",
            f"- cache_path_preflight_cache_write_approval_status: {provider_block['cache_path_preflight_approval_package_status']['cache_write_approval_status']}",
            f"- cache_path_preflight_actual_import_approval_status: {provider_block['cache_path_preflight_approval_package_status']['actual_import_approval_status']}",
            f"- cache_path_preflight_approval_phrase_issued: {str(provider_block['cache_path_preflight_approval_package_status']['approval_phrase_issued']).lower()}",
            f"- cache_purge_inventory_dryrun_contract_exists: {str(provider_block['cache_purge_inventory_dryrun_contract_status']['contract_exists']).lower()}",
            f"- cache_purge_inventory_contract_verdict: {provider_block['cache_purge_inventory_dryrun_contract_status']['contract_verdict']}",
            f"- cache_purge_inventory_redacted_manifest_schema_status: {provider_block['cache_purge_inventory_dryrun_contract_status']['redacted_manifest_schema_status']}",
            f"- cache_purge_inventory_purge_execution_status: {provider_block['cache_purge_inventory_dryrun_contract_status']['purge_execution_status']}",
            f"- cache_purge_inventory_file_deletion_executed: {str(provider_block['cache_purge_inventory_dryrun_contract_status']['file_deletion_executed']).lower()}",
            f"- cache_purge_inventory_raw_ohlcv_read: {str(provider_block['cache_purge_inventory_dryrun_contract_status']['raw_ohlcv_read']).lower()}",
            f"- cache_write_pilot_approval_packet_exists: {str(provider_block['cache_write_pilot_approval_packet_status']['packet_exists']).lower()}",
            f"- cache_write_pilot_packet_verdict: {provider_block['cache_write_pilot_approval_packet_status']['packet_verdict']}",
            f"- cache_write_pilot_provider: {provider_block['cache_write_pilot_approval_packet_status']['provider']}",
            f"- cache_write_pilot_first_subset: {', '.join(provider_block['cache_write_pilot_approval_packet_status']['first_subset'])}",
            f"- cache_write_pilot_candidate_path: {provider_block['cache_write_pilot_approval_packet_status']['candidate_cache_path']}",
            f"- cache_write_pilot_cache_write_approval_status: {provider_block['cache_write_pilot_approval_packet_status']['cache_write_approval_status']}",
            f"- cache_write_pilot_actual_import_approval_status: {provider_block['cache_write_pilot_approval_packet_status']['actual_import_approval_status']}",
            f"- cache_write_pilot_approval_phrase_issued: {str(provider_block['cache_write_pilot_approval_packet_status']['approval_phrase_issued']).lower()}",
            f"- cache_write_pilot_result_review_gate_exists: {str(provider_block['cache_write_pilot_result_review_gate_status']['gate_exists']).lower()}",
            f"- cache_write_pilot_result_review_current_verdict: {provider_block['cache_write_pilot_result_review_gate_status']['current_verdict']}",
            f"- cache_write_pilot_result_review_pilot_has_run: {str(provider_block['cache_write_pilot_result_review_gate_status']['pilot_has_run']).lower()}",
            f"- cache_write_pilot_result_review_actual_import_readiness: {provider_block['cache_write_pilot_result_review_gate_status']['actual_import_readiness']}",
            f"- cache_write_pilot_result_review_raw_ohlcv_emitted: {str(provider_block['cache_write_pilot_result_review_gate_status']['raw_ohlcv_emitted']).lower()}",
            f"- actual_import_readiness_boundary_exists: {str(provider_block['actual_import_readiness_boundary_status']['boundary_exists']).lower()}",
            f"- actual_import_boundary_status: {provider_block['actual_import_readiness_boundary_status']['boundary_status']}",
            f"- actual_import_boundary_cache_write_pilot_readiness: {provider_block['actual_import_readiness_boundary_status']['cache_write_pilot_readiness']}",
            f"- actual_import_boundary_result_review_readiness: {provider_block['actual_import_readiness_boundary_status']['cache_write_pilot_result_review_readiness']}",
            f"- actual_import_boundary_actual_import_readiness: {provider_block['actual_import_readiness_boundary_status']['actual_import_readiness']}",
            f"- actual_import_boundary_cache_write_does_not_imply_actual_import: {str(provider_block['actual_import_readiness_boundary_status']['cache_write_approval_does_not_imply_actual_import']).lower()}",
            f"- actual_import_boundary_result_review_pass_not_sufficient: {str(provider_block['actual_import_readiness_boundary_status']['result_review_pass_not_sufficient_for_actual_import']).lower()}",
            f"- actual_import_boundary_actual_import_approval_phrase_issued: {str(provider_block['actual_import_readiness_boundary_status']['actual_import_approval_phrase_issued']).lower()}",
            f"- actual_import_boundary_execution_allowed_now: {str(provider_block['actual_import_readiness_boundary_status']['actual_import_execution_allowed_now']).lower()}",
            f"- actual_import_boundary_trading_readiness: {provider_block['actual_import_readiness_boundary_status']['trading_readiness']}",
            f"- weekly_report_schedule_diagnostic_exists: {str(out_json['weekly_report_schedule_diagnostic_status']['diagnostic_exists']).lower()}",
            f"- weekly_report_missing_user_observed_issue: {out_json['weekly_report_schedule_diagnostic_status']['user_observed_issue']}",
            f"- weekly_report_missing_root_cause_found: {out_json['weekly_report_schedule_diagnostic_status']['root_cause_found']}",
            f"- weekly_report_github_weekly_schedule_found: {str(out_json['weekly_report_schedule_diagnostic_status']['github_weekly_schedule_found']).lower()}",
            f"- weekly_report_launchd_template_exists: {str(out_json['weekly_report_schedule_diagnostic_status']['launchd_template_exists']).lower()}",
            f"- weekly_report_workflow_change_required: {out_json['weekly_report_schedule_diagnostic_status']['workflow_change_required']}",
            f"- weekly_report_next_scheduled_report_confidence: {out_json['weekly_report_schedule_diagnostic_status']['next_scheduled_report_confidence']}",
            f"- weekly_report_workflow_files_modified: {str(out_json['weekly_report_schedule_diagnostic_status']['workflow_files_modified']).lower()}",
            f"- scheduled_report_observability_exists: {str(out_json['scheduled_report_observability_status']['sentinel_exists']).lower()}",
            f"- scheduled_report_expected_date: {out_json['scheduled_report_observability_status']['expected_date']}",
            f"- scheduled_report_missing_verdict: {out_json['scheduled_report_observability_status']['missing_report_verdict']}",
            f"- scheduled_report_github_actions_cron_utc: {out_json['scheduled_report_observability_status']['github_actions_cron_utc']}",
            f"- scheduled_report_raw_market_data_read: {str(out_json['scheduled_report_observability_status']['raw_market_data_read']).lower()}",
            f"- scheduled_report_workflow_files_modified: {str(out_json['scheduled_report_observability_status']['workflow_files_modified']).lower()}",
            f"- scheduled_report_gmail_send_executed: {str(out_json['scheduled_report_observability_status']['gmail_send_executed']).lower()}",
            f"- weekly_report_recovery_runbook_exists: {str(out_json['weekly_report_recovery_runbook_status']['runbook_exists']).lower()}",
            f"- weekly_report_recovery_missed_report_date: {out_json['weekly_report_recovery_runbook_status']['missed_report_date']}",
            f"- weekly_report_recovery_pack_approves_backfill: {str(out_json['weekly_report_recovery_runbook_status']['this_pack_approves_backfill_execution']).lower()}",
            f"- weekly_report_recovery_manual_backfill_requires_human_choice: {str(out_json['weekly_report_recovery_runbook_status']['manual_backfill_requires_human_choice']).lower()}",
            f"- weekly_report_recovery_workflow_files_modified: {str(out_json['weekly_report_recovery_runbook_status']['workflow_files_modified']).lower()}",
            f"- weekly_report_recovery_gmail_send_executed: {str(out_json['weekly_report_recovery_runbook_status']['gmail_send_executed']).lower()}",
            f"- weekly_report_recovery_provider_live_access_executed: {str(out_json['weekly_report_recovery_runbook_status']['provider_live_access_executed']).lower()}",
            f"- weekly_report_workflow_approval_package_exists: {str(out_json['weekly_report_workflow_approval_package_status']['package_exists']).lower()}",
            f"- weekly_report_workflow_approval_verdict: {out_json['weekly_report_workflow_approval_package_status']['readiness_verdict']}",
            f"- weekly_report_workflow_patch_required: {str(out_json['weekly_report_workflow_approval_package_status']['workflow_patch_required']).lower()}",
            f"- weekly_report_workflow_wrong_cron_detected: {str(out_json['weekly_report_workflow_approval_package_status']['wrong_cron_detected']).lower()}",
            f"- weekly_report_workflow_github_actions_cron_utc: {out_json['weekly_report_workflow_approval_package_status']['github_actions_cron_utc']}",
            f"- weekly_report_workflow_files_modified: {str(out_json['weekly_report_workflow_approval_package_status']['workflow_files_modified']).lower()}",
            f"- weekly_report_local_dryrun_backfill_contract_exists: {str(out_json['weekly_report_local_dryrun_backfill_contract_status']['contract_exists']).lower()}",
            f"- weekly_report_local_dryrun_backfill_verdict: {out_json['weekly_report_local_dryrun_backfill_contract_status']['readiness_verdict']}",
            f"- weekly_report_local_dryrun_missed_report_date: {out_json['weekly_report_local_dryrun_backfill_contract_status']['missed_report_date']}",
            f"- weekly_report_local_dryrun_execution_approved: {str(out_json['weekly_report_local_dryrun_backfill_contract_status']['local_dryrun_execution_approved_by_this_pack']).lower()}",
            f"- weekly_report_manual_backfill_execution_approved: {str(out_json['weekly_report_local_dryrun_backfill_contract_status']['manual_backfill_execution_approved_by_this_pack']).lower()}",
            f"- weekly_report_local_dryrun_raw_ohlcv_persistence_executed: {str(out_json['weekly_report_local_dryrun_backfill_contract_status']['raw_ohlcv_persistence_executed']).lower()}",
            f"- weekly_report_local_dryrun_workflow_files_modified: {str(out_json['weekly_report_local_dryrun_backfill_contract_status']['workflow_files_modified']).lower()}",
            f"- long_run_operator_preflight_sleep_guard_exists: {str(out_json['long_run_operator_preflight_sleep_guard_status']['pack_exists']).lower()}",
            f"- long_run_operator_preflight_verdict: {out_json['long_run_operator_preflight_sleep_guard_status']['readiness_verdict']}",
            f"- long_run_operator_preflight_caffeinate_command: {out_json['long_run_operator_preflight_sleep_guard_status']['recommended_command']}",
            f"- long_run_operator_preflight_future_long_run_include_sleep_guard: {str(out_json['long_run_operator_preflight_sleep_guard_status']['future_long_run_max_instructions_include_sleep_guard']).lower()}",
            f"- long_run_operator_preflight_macos_settings_changed: {str(out_json['long_run_operator_preflight_sleep_guard_status']['macos_system_settings_changed']).lower()}",
            f"- long_run_operator_preflight_workflow_files_modified: {str(out_json['long_run_operator_preflight_sleep_guard_status']['workflow_files_modified']).lower()}",
            f"- scheduled_report_assurance_snapshot_exists: {str(out_json['scheduled_report_assurance_snapshot_status']['snapshot_exists']).lower()}",
            f"- scheduled_report_assurance_verdict: {out_json['scheduled_report_assurance_snapshot_status']['readiness_verdict']}",
            f"- scheduled_report_assurance_next_run_date_jst: {out_json['scheduled_report_assurance_snapshot_status']['next_run_date_jst']}",
            f"- scheduled_report_assurance_next_run_local_time: {out_json['scheduled_report_assurance_snapshot_status']['next_run_local_time']}",
            f"- scheduled_report_assurance_cron_utc: {out_json['scheduled_report_assurance_snapshot_status']['github_actions_cron_utc']}",
            f"- scheduled_report_assurance_confidence: {out_json['scheduled_report_assurance_snapshot_status']['next_scheduled_report_confidence']}",
            f"- scheduled_report_assurance_workflow_files_modified: {str(out_json['scheduled_report_assurance_snapshot_status']['workflow_files_modified']).lower()}",
            f"- scheduled_report_assurance_gmail_send_executed: {str(out_json['scheduled_report_assurance_snapshot_status']['gmail_send_executed']).lower()}",
            f"- weekly_report_workflow_patch_review_gate_exists: {str(out_json['weekly_report_workflow_patch_review_gate_status']['gate_exists']).lower()}",
            f"- weekly_report_workflow_patch_review_verdict: {out_json['weekly_report_workflow_patch_review_gate_status']['readiness_verdict']}",
            f"- weekly_report_workflow_patch_review_human_approval_required: {str(out_json['weekly_report_workflow_patch_review_gate_status']['human_approval_required']).lower()}",
            f"- weekly_report_workflow_patch_review_utc_cron: {out_json['weekly_report_workflow_patch_review_gate_status']['utc_cron_expression']}",
            f"- weekly_report_workflow_patch_review_jst_schedule: {out_json['weekly_report_workflow_patch_review_gate_status']['corresponding_jst_schedule']}",
            f"- weekly_report_workflow_patch_review_manual_dispatch_required: {str(out_json['weekly_report_workflow_patch_review_gate_status']['manual_workflow_dispatch_required']).lower()}",
            f"- weekly_report_workflow_patch_review_workflow_files_modified: {str(out_json['weekly_report_workflow_patch_review_gate_status']['workflow_files_modified']).lower()}",
            f"- weekly_report_manual_backfill_command_pack_exists: {str(out_json['weekly_report_manual_backfill_command_pack_status']['pack_exists']).lower()}",
            f"- weekly_report_manual_backfill_command_pack_verdict: {out_json['weekly_report_manual_backfill_command_pack_status']['readiness_verdict']}",
            f"- weekly_report_manual_backfill_missed_report_date: {out_json['weekly_report_manual_backfill_command_pack_status']['missed_report_date']}",
            f"- weekly_report_manual_backfill_timezone: {out_json['weekly_report_manual_backfill_command_pack_status']['timezone']}",
            f"- weekly_report_manual_backfill_execution_approved: {str(out_json['weekly_report_manual_backfill_command_pack_status']['manual_backfill_execution_approved_by_this_pack']).lower()}",
            f"- weekly_report_manual_backfill_raw_data_outputs_allowed: {str(out_json['weekly_report_manual_backfill_command_pack_status']['raw_data_outputs_allowed']).lower()}",
            f"- weekly_report_manual_backfill_workflow_files_modified: {str(out_json['weekly_report_manual_backfill_command_pack_status']['workflow_files_modified']).lower()}",
            f"- weekly_report_manual_backfill_gmail_send_executed: {str(out_json['weekly_report_manual_backfill_command_pack_status']['gmail_send_executed']).lower()}",
            f"- scheduled_report_failure_triage_matrix_exists: {str(out_json['scheduled_report_failure_triage_matrix_status']['matrix_exists']).lower()}",
            f"- scheduled_report_failure_triage_verdict: {out_json['scheduled_report_failure_triage_matrix_status']['readiness_verdict']}",
            f"- scheduled_report_failure_triage_classes: {', '.join(out_json['scheduled_report_failure_triage_matrix_status']['failure_classes'])}",
            f"- scheduled_report_failure_triage_utc_cron: {out_json['scheduled_report_failure_triage_matrix_status']['utc_cron_expression']}",
            f"- scheduled_report_failure_triage_secret_values_may_be_displayed: {str(out_json['scheduled_report_failure_triage_matrix_status']['secret_values_may_be_displayed']).lower()}",
            f"- scheduled_report_failure_triage_workflow_files_modified: {str(out_json['scheduled_report_failure_triage_matrix_status']['workflow_files_modified']).lower()}",
            f"- long_run_development_progress_snapshot_exists: {str(out_json['long_run_development_progress_snapshot_status']['snapshot_exists']).lower()}",
            f"- long_run_development_progress_verdict: {out_json['long_run_development_progress_snapshot_status']['readiness_verdict']}",
            f"- long_run_development_single_overall_percent_allowed: {str(out_json['long_run_development_progress_snapshot_status']['single_overall_percent_allowed']).lower()}",
            f"- long_run_development_progress_domains: {', '.join(out_json['long_run_development_progress_snapshot_status']['domains'])}",
            f"- long_run_development_progress_workflow_files_modified: {str(out_json['long_run_development_progress_snapshot_status']['workflow_files_modified']).lower()}",
            f"- weekly_workflow_post_merge_observation_plan_exists: {str(out_json['weekly_workflow_post_merge_observation_plan_status']['plan_exists']).lower()}",
            f"- weekly_workflow_post_merge_observation_verdict: {out_json['weekly_workflow_post_merge_observation_plan_status']['readiness_verdict']}",
            f"- weekly_workflow_post_merge_next_run_date_jst: {out_json['weekly_workflow_post_merge_observation_plan_status']['next_run_date_jst']}",
            f"- weekly_workflow_post_merge_next_run_local_time: {out_json['weekly_workflow_post_merge_observation_plan_status']['next_run_local_time']}",
            f"- weekly_workflow_post_merge_cron_utc: {out_json['weekly_workflow_post_merge_observation_plan_status']['github_actions_cron_utc']}",
            f"- weekly_workflow_post_merge_workflow_exists: {str(out_json['weekly_workflow_post_merge_observation_plan_status']['workflow_exists']).lower()}",
            f"- weekly_workflow_post_merge_expected_cron_found: {str(out_json['weekly_workflow_post_merge_observation_plan_status']['expected_cron_found']).lower()}",
            f"- weekly_workflow_post_merge_manual_dispatch_executed: {str(out_json['weekly_workflow_post_merge_observation_plan_status']['manual_workflow_dispatch_executed']).lower()}",
            f"- weekly_workflow_post_merge_workflow_files_modified: {str(out_json['weekly_workflow_post_merge_observation_plan_status']['workflow_files_modified']).lower()}",
            "",
            "## 7. ChatGPTへの推奨質問",
            "- 上位3銘柄の無効化条件を先に定義してください。",
            "- staleデータ銘柄を除いた場合の優先順位を提案してください。",
            "",
        ]
    )
    return ContextPackResult(markdown_text="\n".join(md_lines).rstrip() + "\n", json_payload=out_json)
