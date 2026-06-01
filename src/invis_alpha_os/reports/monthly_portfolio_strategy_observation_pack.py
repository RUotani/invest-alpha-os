"""Source-only monthly portfolio strategy observation pack v78.

This module supports human-redacted monthly portfolio snapshots and
observation-only allocation strategy reports. It intentionally avoids broker
exports, broker APIs, live market data, cache writes, imports, and trading
execution wording.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

PACK_VERSION = "v78"
DEFAULT_REPORT_MONTH = "2026-05"
DEFAULT_SNAPSHOT_DATE = "2026-05-31"
DEFAULT_UNIT = "万円"

REQUIRED_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "report_month",
    "snapshot_date",
    "unit",
    "total_assets",
    "liabilities_or_mortgage",
    "net_worth",
    "cash",
    "index_funds",
    "individual_stocks",
    "bonds",
    "gold",
    "crypto_or_high_beta",
    "leveraged",
    "notes",
    "data_corrections",
)

ASSET_BUCKET_FIELDS: tuple[str, ...] = (
    "cash",
    "index_funds",
    "individual_stocks",
    "bonds",
    "gold",
    "crypto_or_high_beta",
    "leveraged",
)

NUMERIC_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "total_assets",
    "liabilities_or_mortgage",
    "net_worth",
    *ASSET_BUCKET_FIELDS,
)

FORBIDDEN_FIELD_TOKENS: tuple[str, ...] = (
    "broker",
    "account_number",
    "branch_code",
    "login",
    "password",
    "token",
    "secret",
    "api_key",
    "raw_export",
    "raw_broker",
    "order_id",
    "trade_id",
    "execution_id",
    "env",
    "口座番号",
    "ログイン",
    "パスワード",
    "注文番号",
    "約定番号",
)

FORBIDDEN_VALUE_TOKENS: tuple[str, ...] = (
    "password=",
    "token=",
    "api_key=",
    "secret=",
    "broker login",
    "raw broker export",
    "raw_export",
    "place order",
    "execute order",
    "market order",
    "limit order",
    "cache write",
    "actual refresh",
    "actual import",
    "live price fetched",
    "live http",
    "証券口座番号",
    "成行注文",
    "指値注文",
    "発注する",
)

TOTAL_TOLERANCE_ABS = 0.2
PERCENT_TOLERANCE_ABS = 0.2

GUARDRAIL_ROWS: tuple[dict[str, Any], ...] = (
    {
        "bucket": "cash",
        "display_name": "cash",
        "min_pct": 15.0,
        "max_pct": 25.0,
        "reference": "near-term recovery band; long-term preference around 30% remains a reference",
        "under_action": "rebuild_cash_buffer",
        "over_action": "reduce_idle_cash_only_after_core_plan_review",
        "within_action": "keep_cash_buffer_monitored",
    },
    {
        "bucket": "index_funds",
        "display_name": "core index",
        "min_pct": 50.0,
        "max_pct": 60.0,
        "reference": "core should be mutual funds, broad ETFs, and index exposure",
        "under_action": "keep_core_contributions_disciplined",
        "over_action": "do_not_expand_core_without_cash_review",
        "within_action": "keep_core_contributions_disciplined",
    },
    {
        "bucket": "individual_stocks",
        "display_name": "individual stocks",
        "min_pct": 10.0,
        "max_pct": 15.0,
        "reference": "preferred satellite maximum band",
        "under_action": "do_not_expand_satellite_without_rebalancing",
        "over_action": "review_sell_candidates",
        "within_action": "reduce_new_buying_pressure",
    },
    {
        "bucket": "bonds",
        "display_name": "bonds",
        "min_pct": 10.0,
        "max_pct": 15.0,
        "reference": "stabilizer band",
        "under_action": "review_defensive_buffer",
        "over_action": "review_duration_concentration",
        "within_action": "keep_defensive_bucket_monitored",
    },
    {
        "bucket": "gold",
        "display_name": "gold / alternatives",
        "min_pct": 5.0,
        "max_pct": 10.0,
        "reference": "alternative stabilizer band",
        "under_action": "watch_alternative_buffer",
        "over_action": "review_alternative_concentration",
        "within_action": "keep_alternative_buffer_monitored",
    },
    {
        "bucket": "crypto_or_high_beta",
        "display_name": "crypto / high-beta proxy",
        "min_pct": 0.0,
        "max_pct": 5.0,
        "reference": "risk satellite only",
        "under_action": "no_action_required",
        "over_action": "review_high_beta_cleanup_candidates",
        "within_action": "do_not_expand_satellite_without_rebalancing",
    },
    {
        "bucket": "leveraged",
        "display_name": "leveraged",
        "min_pct": 0.0,
        "max_pct": 5.0,
        "reference": "requires explicit path-dependency risk note even inside band",
        "under_action": "no_action_required",
        "over_action": "review_sell_candidates",
        "within_action": "exit_rule_required",
    },
)

CLEANUP_CRITERIA: tuple[str, ...] = (
    "not_long_term_holdable",
    "thesis_unclear",
    "timing_missed",
    "leveraged_decay_or_path_dependency",
    "poor_performance_vs_core_index",
    "requires_frequent_monitoring",
    "position_size_too_large",
    "cash_buffer_pressure",
    "tax_offset_context_available",
)


def _safety_summary() -> dict[str, bool]:
    return {
        "provider_live_access_executed": False,
        "live_http_executed": False,
        "tiingo_api_call_executed": False,
        "stooq_yahoo_polygon_live_fetch_executed": False,
        "cache_write_executed": False,
        "cache_directory_created": False,
        "actual_refresh_import_executed": False,
        "manual_actual_import_executed": False,
        "broker_api_access_executed": False,
        "broker_login_executed": False,
        "raw_broker_export_parsed": False,
        "raw_broker_data_persisted": False,
        "raw_excel_direct_parsed": False,
        "raw_ohlcv_api_persistence_executed": False,
        "reports_private_raw_data_written": False,
        "git_tracked_raw_data_written": False,
        "env_secret_displayed": False,
        "workflow_files_modified": False,
        "dependency_pyproject_changed": False,
        "github_settings_changed": False,
        "trading_action_executed": False,
        "order_placement_executed": False,
        "manual_workflow_dispatch_executed": False,
    }


def _payload_base(*, report_month: str, report_name: str) -> dict[str, Any]:
    return {
        "pack_version": PACK_VERSION,
        "report_name": report_name,
        "source_only": True,
        "observation_only": True,
        "report_month": report_month,
    }


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_pct(value: float) -> float:
    return round(value, 1)


def _walk_fields(value: Any, *, prefix: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        rows: list[tuple[str, Any]] = []
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            rows.append((path, item))
            rows.extend(_walk_fields(item, prefix=path))
        return rows
    if isinstance(value, list):
        rows = []
        for idx, item in enumerate(value):
            rows.extend(_walk_fields(item, prefix=f"{prefix}[{idx}]"))
        return rows
    return []


def detect_monthly_snapshot_forbidden_fields(snapshot: dict[str, Any]) -> tuple[str, ...]:
    hits: set[str] = set()
    for path, _value in _walk_fields(snapshot):
        leaf = path.split(".")[-1].lower()
        for token in FORBIDDEN_FIELD_TOKENS:
            if token in leaf:
                hits.add(path)
                break
    return tuple(sorted(hits))


def detect_monthly_snapshot_forbidden_values(snapshot: dict[str, Any]) -> tuple[str, ...]:
    hits: set[str] = set()

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                visit(item, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                visit(item, f"{path}[{idx}]")
        elif isinstance(value, str):
            lowered = value.lower()
            for token in FORBIDDEN_VALUE_TOKENS:
                if token in lowered:
                    hits.add(path)
                    break

    visit(snapshot, "")
    return tuple(sorted(hits))


def default_monthly_portfolio_snapshot(*, report_month: str, snapshot_date: str | None = None) -> dict[str, Any]:
    if report_month != DEFAULT_REPORT_MONTH:
        return {
            "report_month": report_month,
            "snapshot_date": snapshot_date or f"{report_month}-month-end",
            "unit": DEFAULT_UNIT,
            "total_assets": 0,
            "liabilities_or_mortgage": 0,
            "net_worth": 0,
            "cash": 0,
            "index_funds": 0,
            "individual_stocks": 0,
            "bonds": 0,
            "gold": 0,
            "crypto_or_high_beta": 0,
            "leveraged": 0,
            "allocation_pct": {},
            "notes": "manual redacted monthly input placeholder; source-only summary, not an export",
            "data_corrections": [],
        }
    return {
        "report_month": DEFAULT_REPORT_MONTH,
        "snapshot_date": snapshot_date or DEFAULT_SNAPSHOT_DATE,
        "unit": DEFAULT_UNIT,
        "total_assets": 4327.9,
        "liabilities_or_mortgage": 3432.0,
        "net_worth": 895.9,
        "cash": 508.2,
        "index_funds": 2088.2,
        "individual_stocks": 846.3,
        "bonds": 582.7,
        "gold": 234.5,
        "crypto_or_high_beta": 57.5,
        "leveraged": 10.5,
        "allocation_pct": {
            "cash": 11.7,
            "index_funds": 48.2,
            "individual_stocks": 19.6,
            "bonds": 13.5,
            "gold": 5.4,
            "crypto_or_high_beta": 1.3,
            "leveraged": 0.2,
        },
        "notes": (
            "human-confirmed 2026-05 month-end approximate allocation; unit is 万円; "
            "manual/redacted context only"
        ),
        "data_corrections": [
            {
                "field": "OLC",
                "incorrect_value": 224.0,
                "corrected_value": 22.4,
                "unit": DEFAULT_UNIT,
                "note": "OLC was a data-entry mistake; 22.4万円 is the human-confirmed value.",
            }
        ],
    }


def load_monthly_portfolio_snapshot_json(path: Path) -> dict[str, Any]:
    """Load a human-created redacted monthly snapshot JSON object."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("monthly portfolio snapshot JSON must be an object")
    return data


def derived_allocation_pct(snapshot: dict[str, Any]) -> dict[str, float]:
    total = _as_float(snapshot.get("total_assets"))
    if total is None or total <= 0:
        return {field: 0.0 for field in ASSET_BUCKET_FIELDS}
    rows: dict[str, float] = {}
    for field in ASSET_BUCKET_FIELDS:
        value = _as_float(snapshot.get(field)) or 0.0
        rows[field] = _round_pct(value / total * 100.0)
    return rows


def _snapshot_missing_fields(snapshot: dict[str, Any]) -> tuple[str, ...]:
    return tuple(field for field in REQUIRED_SNAPSHOT_FIELDS if field not in snapshot)


def _total_consistency_checks(snapshot: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    checks: list[dict[str, Any]] = []
    total_assets = _as_float(snapshot.get("total_assets"))
    liabilities = _as_float(snapshot.get("liabilities_or_mortgage"))
    net_worth = _as_float(snapshot.get("net_worth"))
    asset_sum = sum((_as_float(snapshot.get(field)) or 0.0) for field in ASSET_BUCKET_FIELDS)
    if total_assets is not None:
        checks.append(
            {
                "check": "total_assets_matches_asset_buckets",
                "pass": abs(total_assets - asset_sum) <= TOTAL_TOLERANCE_ABS,
                "expected": round(asset_sum, 4),
                "actual": total_assets,
            }
        )
    if total_assets is not None and liabilities is not None and net_worth is not None:
        expected_net_worth = total_assets - liabilities
        checks.append(
            {
                "check": "net_worth_matches_assets_minus_liabilities",
                "pass": abs(net_worth - expected_net_worth) <= TOTAL_TOLERANCE_ABS,
                "expected": round(expected_net_worth, 4),
                "actual": net_worth,
            }
        )
    return tuple(checks)


def _percent_consistency_checks(snapshot: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    provided = snapshot.get("allocation_pct") or snapshot.get("percent_allocation") or {}
    if not isinstance(provided, dict) or not provided:
        return ()
    derived = derived_allocation_pct(snapshot)
    checks: list[dict[str, Any]] = []
    for field in ASSET_BUCKET_FIELDS:
        if field not in provided:
            continue
        expected = derived[field]
        actual = _as_float(provided.get(field))
        checks.append(
            {
                "check": f"{field}_pct_matches_amount_over_total_assets",
                "pass": actual is not None and abs(actual - expected) <= PERCENT_TOLERANCE_ABS,
                "expected": expected,
                "actual": actual,
            }
        )
    return tuple(checks)


def validate_monthly_portfolio_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    missing = _snapshot_missing_fields(snapshot)
    forbidden_fields = detect_monthly_snapshot_forbidden_fields(snapshot)
    forbidden_values = detect_monthly_snapshot_forbidden_values(snapshot)
    field_errors: list[str] = []
    for field in NUMERIC_SNAPSHOT_FIELDS:
        if field in snapshot:
            value = _as_float(snapshot[field])
            if value is None:
                field_errors.append(f"{field}_not_numeric")
            elif value < 0:
                field_errors.append(f"{field}_negative")
    data_corrections = snapshot.get("data_corrections")
    if "data_corrections" in snapshot and not isinstance(data_corrections, list):
        field_errors.append("data_corrections_must_be_list")
    if "notes" in snapshot and not isinstance(snapshot.get("notes"), str):
        field_errors.append("notes_must_be_string")
    if str(snapshot.get("unit", "")).strip() not in {"万円", "JPY", "yen", "manual_unit"}:
        field_errors.append("unit_not_supported")
    correction_notes_present = isinstance(data_corrections, list) and all(
        isinstance(row, dict) and str(row.get("note") or row.get("reason") or "").strip()
        for row in data_corrections
    )
    total_checks = _total_consistency_checks(snapshot)
    pct_checks = _percent_consistency_checks(snapshot)
    failed_checks = tuple(row for row in (*total_checks, *pct_checks) if not row["pass"])
    validation_passed = (
        not missing
        and not field_errors
        and not forbidden_fields
        and not forbidden_values
        and not failed_checks
    )
    return {
        **_payload_base(
            report_month=str(snapshot.get("report_month", "")),
            report_name="monthly_portfolio_snapshot_validation",
        ),
        "validation_passed": validation_passed,
        "chatgpt_paste_ready": validation_passed,
        "top_level_missing_fields": missing,
        "field_errors": tuple(field_errors),
        "forbidden_fields_detected": forbidden_fields,
        "forbidden_values_detected": forbidden_values,
        "total_consistency_checks": total_checks,
        "percent_consistency_checks": pct_checks,
        "derived_allocation_pct": derived_allocation_pct(snapshot),
        "correction_notes_present": correction_notes_present,
        "raw_data_boundary": {
            "raw_broker_export_parser": False,
            "raw_excel_direct_parser": False,
            "manual_redacted_json_only": True,
            "live_data_assumption_allowed": False,
        },
        "safety_summary": _safety_summary(),
    }


def build_monthly_portfolio_snapshot_template(
    *,
    report_month: str,
    snapshot_date: str | None = None,
) -> dict[str, Any]:
    snapshot = default_monthly_portfolio_snapshot(report_month=report_month, snapshot_date=snapshot_date)
    return {
        **_payload_base(report_month=report_month, report_name="monthly_portfolio_snapshot_template"),
        "monthly_portfolio_snapshot": snapshot,
        "field_contract": {
            "required_fields": REQUIRED_SNAPSHOT_FIELDS,
            "numeric_fields": NUMERIC_SNAPSHOT_FIELDS,
            "asset_bucket_fields": ASSET_BUCKET_FIELDS,
            "optional_percent_field": "allocation_pct",
            "unit_policy": "manual monthly values; default unit is 万円",
        },
        "validation_contract": {
            "total_consistency": "asset buckets must sum to total_assets within tolerance",
            "net_worth_consistency": "net_worth must equal total_assets - liabilities_or_mortgage within tolerance",
            "percent_consistency": "allocation_pct, when supplied, must match amount / total_assets",
            "correction_notes": "data_corrections must be a list and should document known manual corrections",
            "source_boundary": "manual/redacted JSON only; no broker exports, Excel parsing, live data, or secrets",
        },
        "copy_ready_chatgpt_prompt": (
            "この月次ポートフォリオsnapshotを使い、core/satellite配分、現金バッファ、"
            "個別株比率、cleanup候補を観測してください。売買指示・発注手順は出さないでください。"
        ),
        "safety_summary": _safety_summary(),
    }


def _guardrail_status(pct: float, *, minimum: float, maximum: float, bucket: str) -> tuple[str, str]:
    if pct < minimum:
        return "underweight", "action_required_observation_only"
    if pct > maximum:
        return "overweight", "action_required_observation_only"
    if bucket == "leveraged" and pct > 0:
        return "watch", "watch"
    return "within_band", "within_band"


def build_monthly_portfolio_allocation_guardrails(
    *,
    report_month: str,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_snapshot = copy.deepcopy(snapshot) if snapshot is not None else default_monthly_portfolio_snapshot(
        report_month=report_month,
        snapshot_date=None,
    )
    validation = validate_monthly_portfolio_snapshot(current_snapshot)
    allocation = validation["derived_allocation_pct"]
    rows: list[dict[str, Any]] = []
    for guardrail in GUARDRAIL_ROWS:
        bucket = str(guardrail["bucket"])
        pct = float(allocation[bucket])
        band_status, classification = _guardrail_status(
            pct,
            minimum=float(guardrail["min_pct"]),
            maximum=float(guardrail["max_pct"]),
            bucket=bucket,
        )
        if band_status == "underweight":
            observation_action = str(guardrail["under_action"])
        elif band_status == "overweight":
            observation_action = str(guardrail["over_action"])
        else:
            observation_action = str(guardrail["within_action"])
        rows.append(
            {
                "bucket": bucket,
                "display_name": guardrail["display_name"],
                "amount": current_snapshot.get(bucket),
                "allocation_pct": pct,
                "target_min_pct": guardrail["min_pct"],
                "target_max_pct": guardrail["max_pct"],
                "band_status": band_status,
                "classification": classification,
                "observation_action": observation_action,
                "reference": guardrail["reference"],
                "not_a_trade_instruction": True,
            }
        )
    action_required = any(row["classification"] == "action_required_observation_only" for row in rows)
    return {
        **_payload_base(report_month=report_month, report_name="monthly_portfolio_allocation_guardrails"),
        "snapshot_validation": validation,
        "guardrail_rows": tuple(rows),
        "portfolio_guardrail_summary": {
            "overall_classification": "action_required_observation_only" if action_required else "watch",
            "cash_buffer_warning": next(row for row in rows if row["bucket"] == "cash")["band_status"]
            != "within_band",
            "individual_stock_exposure_note": next(row for row in rows if row["bucket"] == "individual_stocks")[
                "band_status"
            ],
            "allowed_observation_actions": (
                "reduce_new_buying_pressure",
                "review_sell_candidates",
                "rebuild_cash_buffer",
                "keep_core_contributions_disciplined",
                "do_not_expand_satellite_without_rebalancing",
            ),
            "trading_instruction_allowed": False,
        },
        "safety_summary": _safety_summary(),
    }


def build_portfolio_cleanup_candidate_matrix(*, report_month: str) -> dict[str, Any]:
    examples = (
        {
            "symbol_or_label": "TMF",
            "role": "time_sensitive_leveraged_example",
            "triggered_criteria": (
                "timing_missed",
                "leveraged_decay_or_path_dependency",
                "requires_frequent_monitoring",
                "cash_buffer_pressure",
            ),
            "label": "exit_rule_required",
            "observation_action": "define_observation_exit_rule_before_adding",
        },
        {
            "symbol_or_label": "theme_stock_example",
            "role": "learning_satellite_example",
            "triggered_criteria": (
                "thesis_unclear",
                "poor_performance_vs_core_index",
                "requires_frequent_monitoring",
            ),
            "label": "cleanup_candidate",
            "observation_action": "review_sell_candidates",
        },
        {
            "symbol_or_label": "cyclical_stock_example",
            "role": "cyclical_satellite_example",
            "triggered_criteria": (
                "timing_missed",
                "poor_performance_vs_core_index",
                "tax_offset_context_available",
            ),
            "label": "reduce_on_rebound_candidate",
            "observation_action": "document_rebound_or_cleanup_conditions",
        },
        {
            "symbol_or_label": "long_term_core_example",
            "role": "core_index_or_broad_etf_example",
            "triggered_criteria": (),
            "label": "hold_core",
            "observation_action": "keep_core_contributions_disciplined",
        },
        {
            "symbol_or_label": "oversized_satellite_example",
            "role": "position_size_risk_example",
            "triggered_criteria": (
                "position_size_too_large",
                "cash_buffer_pressure",
                "not_long_term_holdable",
            ),
            "label": "do_not_add",
            "observation_action": "do_not_expand_satellite_without_rebalancing",
        },
    )
    rows = []
    for example in examples:
        triggered = set(example["triggered_criteria"])
        rows.append(
            {
                **example,
                "criteria_matrix": {criterion: criterion in triggered for criterion in CLEANUP_CRITERIA},
                "not_a_sell_instruction": True,
                "live_price_used": False,
            }
        )
    return {
        **_payload_base(report_month=report_month, report_name="portfolio_cleanup_candidate_matrix"),
        "criteria": CLEANUP_CRITERIA,
        "allowed_labels": (
            "hold_core",
            "hold_with_review",
            "cleanup_candidate",
            "reduce_on_rebound_candidate",
            "exit_rule_required",
            "do_not_add",
        ),
        "matrix_rows": tuple(rows),
        "source_boundary": {
            "uses_fixture_examples_only": True,
            "stock_specific_logic_used": False,
            "live_prices_fetched": False,
            "trading_instruction_allowed": False,
        },
        "safety_summary": _safety_summary(),
    }


def build_monthly_chatgpt_portfolio_review_pack(
    *,
    report_month: str,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_snapshot = copy.deepcopy(snapshot) if snapshot is not None else default_monthly_portfolio_snapshot(
        report_month=report_month,
        snapshot_date=None,
    )
    snapshot_validation = validate_monthly_portfolio_snapshot(current_snapshot)
    guardrails = build_monthly_portfolio_allocation_guardrails(
        report_month=report_month,
        snapshot=current_snapshot,
    )
    cleanup = build_portfolio_cleanup_candidate_matrix(report_month=report_month)
    allocation = snapshot_validation["derived_allocation_pct"]
    return {
        **_payload_base(report_month=report_month, report_name="monthly_chatgpt_portfolio_review_pack"),
        "corrected_monthly_allocation_snapshot": current_snapshot,
        "derived_allocation_pct": allocation,
        "snapshot_validation_status": {
            "validation_passed": snapshot_validation["validation_passed"],
            "correction_notes_present": snapshot_validation["correction_notes_present"],
            "raw_data_boundary": snapshot_validation["raw_data_boundary"],
        },
        "core_satellite_guardrails": guardrails["guardrail_rows"],
        "cash_buffer_warning": guardrails["portfolio_guardrail_summary"]["cash_buffer_warning"],
        "individual_stock_exposure_note": guardrails["portfolio_guardrail_summary"][
            "individual_stock_exposure_note"
        ],
        "cleanup_candidate_framework": cleanup["matrix_rows"],
        "generic_position_aware_guard_note": {
            "dca_guard_is_sub_tool": True,
            "dca_deepening_track_closed_after_v76": True,
            "use_for_behavior_control_and_risk_observation": True,
        },
        "main_development_handoff_update": {
            "v78_status": "monthly_portfolio_strategy_observation_source_pack_added",
            "monthly_portfolio_excel_workflow": "human updates Excel near month-end, then transfers redacted manual summary into JSON contract",
            "olc_correction_example": "OLC must be 22.4万円, not 224.0万円, for 2026-05 month-end context",
            "core_satellite_strategy_direction": (
                "core in mutual funds/broad ETFs/index exposure; individual stocks remain learning satellite"
            ),
            "dca_guard_role": "sub-tool_only_not_main_development_track",
            "next_main_development_priorities": (
                "observe 2026-06-06 weekly scheduled run",
                "decide cache-write pilot execution only after explicit approval",
                "continue actual import readiness only after cache-write acceptance",
                "expand portfolio strategy reporting without trading wording",
            ),
        },
        "next_human_inputs_needed": (
            "redacted monthly snapshot JSON after each month-end Excel update",
            "manual notes for known corrections and classification changes",
            "cleanup candidate rationale without broker account identifiers or order history",
        ),
        "observation_only_caveat": (
            "This pack supports ChatGPT portfolio review dialogue only. It is not investment advice, "
            "not a broker instruction, and not an order plan."
        ),
        "safety_summary": _safety_summary(),
    }


def _format_table(rows: tuple[dict[str, Any], ...] | list[dict[str, Any]], columns: tuple[str, ...]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return lines


def _format_safety_summary_lines(payload: dict[str, Any]) -> list[str]:
    return [f"- {key}: {str(value).lower()}" for key, value in payload["safety_summary"].items()]


def format_monthly_portfolio_strategy_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_monthly_portfolio_strategy_markdown(payload: dict[str, Any]) -> str:
    name = payload["report_name"]
    title = name.replace("_", " ").title()
    lines = [
        f"# {title} {PACK_VERSION}",
        "",
        "## Verdict",
        f"- report_name: {name}",
        f"- report_month: {payload['report_month']}",
        f"- source_only: {str(payload['source_only']).lower()}",
        f"- observation_only: {str(payload['observation_only']).lower()}",
        "",
    ]
    if name == "monthly_portfolio_snapshot_template":
        lines.extend(
            [
                "## Snapshot JSON Template",
                "```json",
                json.dumps(payload["monthly_portfolio_snapshot"], ensure_ascii=False, indent=2),
                "```",
                "",
                "## Validation Contract",
            ]
        )
        for key, value in payload["validation_contract"].items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "## Copy-ready ChatGPT Prompt", payload["copy_ready_chatgpt_prompt"]])
    elif name == "monthly_portfolio_snapshot_validation":
        lines.extend(
            [
                "## Validation Status",
                f"- validation_passed: {str(payload['validation_passed']).lower()}",
                f"- chatgpt_paste_ready: {str(payload['chatgpt_paste_ready']).lower()}",
                f"- correction_notes_present: {str(payload['correction_notes_present']).lower()}",
                f"- top_level_missing_fields: {', '.join(payload['top_level_missing_fields']) or 'none'}",
                f"- field_errors: {', '.join(payload['field_errors']) or 'none'}",
                f"- forbidden_fields_detected: {', '.join(payload['forbidden_fields_detected']) or 'none'}",
                f"- forbidden_values_detected: {', '.join(payload['forbidden_values_detected']) or 'none'}",
                "",
                "## Total Consistency Checks",
            ]
        )
        lines.extend(_format_table(list(payload["total_consistency_checks"]), ("check", "pass", "expected", "actual")))
        lines.extend(["", "## Percent Consistency Checks"])
        if payload["percent_consistency_checks"]:
            lines.extend(
                _format_table(list(payload["percent_consistency_checks"]), ("check", "pass", "expected", "actual"))
            )
        else:
            lines.append("- no provided allocation_pct fields to compare")
        lines.extend(["", "## Derived Allocation Percent"])
        for key, value in payload["derived_allocation_pct"].items():
            lines.append(f"- {key}: {value}%")
    elif name == "monthly_portfolio_allocation_guardrails":
        summary = payload["portfolio_guardrail_summary"]
        lines.extend(
            [
                "## Portfolio Guardrail Summary",
                f"- overall_classification: {summary['overall_classification']}",
                f"- cash_buffer_warning: {str(summary['cash_buffer_warning']).lower()}",
                f"- individual_stock_exposure_note: {summary['individual_stock_exposure_note']}",
                "- trading_instruction_allowed: false",
                "",
                "## Guardrail Rows",
            ]
        )
        lines.extend(
            _format_table(
                list(payload["guardrail_rows"]),
                (
                    "display_name",
                    "amount",
                    "allocation_pct",
                    "target_min_pct",
                    "target_max_pct",
                    "band_status",
                    "classification",
                    "observation_action",
                ),
            )
        )
    elif name == "portfolio_cleanup_candidate_matrix":
        lines.extend(
            [
                "## Cleanup Criteria",
                *[f"- {criterion}" for criterion in payload["criteria"]],
                "",
                "## Matrix Rows",
            ]
        )
        lines.extend(
            _format_table(
                list(payload["matrix_rows"]),
                ("symbol_or_label", "role", "triggered_criteria", "label", "observation_action"),
            )
        )
    elif name == "monthly_chatgpt_portfolio_review_pack":
        snapshot = payload["corrected_monthly_allocation_snapshot"]
        handoff = payload["main_development_handoff_update"]
        lines.extend(
            [
                "## Corrected Monthly Allocation Snapshot",
                f"- total_assets: {snapshot['total_assets']} {snapshot['unit']}",
                f"- liabilities_or_mortgage: {snapshot['liabilities_or_mortgage']} {snapshot['unit']}",
                f"- net_worth: {snapshot['net_worth']} {snapshot['unit']}",
                f"- cash: {snapshot['cash']} {snapshot['unit']} ({payload['derived_allocation_pct']['cash']}%)",
                f"- index_funds: {snapshot['index_funds']} {snapshot['unit']} ({payload['derived_allocation_pct']['index_funds']}%)",
                f"- individual_stocks: {snapshot['individual_stocks']} {snapshot['unit']} ({payload['derived_allocation_pct']['individual_stocks']}%)",
                f"- bonds: {snapshot['bonds']} {snapshot['unit']} ({payload['derived_allocation_pct']['bonds']}%)",
                f"- gold: {snapshot['gold']} {snapshot['unit']} ({payload['derived_allocation_pct']['gold']}%)",
                f"- crypto_or_high_beta: {snapshot['crypto_or_high_beta']} {snapshot['unit']} ({payload['derived_allocation_pct']['crypto_or_high_beta']}%)",
                f"- leveraged: {snapshot['leveraged']} {snapshot['unit']} ({payload['derived_allocation_pct']['leveraged']}%)",
                "",
                "## Guardrail Highlights",
                f"- cash_buffer_warning: {str(payload['cash_buffer_warning']).lower()}",
                f"- individual_stock_exposure_note: {payload['individual_stock_exposure_note']}",
                "- observation_only: true",
                "",
                "## Core/Satellite Guardrails",
            ]
        )
        lines.extend(
            _format_table(
                list(payload["core_satellite_guardrails"]),
                ("display_name", "allocation_pct", "band_status", "classification", "observation_action"),
            )
        )
        lines.extend(["", "## Cleanup Candidate Framework"])
        lines.extend(
            _format_table(
                list(payload["cleanup_candidate_framework"]),
                ("symbol_or_label", "label", "observation_action"),
            )
        )
        lines.extend(
            [
                "",
                "## Main Development Handoff Update",
                f"- v78_status: {handoff['v78_status']}",
                f"- monthly_portfolio_excel_workflow: {handoff['monthly_portfolio_excel_workflow']}",
                f"- olc_correction_example: {handoff['olc_correction_example']}",
                f"- core_satellite_strategy_direction: {handoff['core_satellite_strategy_direction']}",
                f"- dca_guard_role: {handoff['dca_guard_role']}",
                "",
                "## Next Human Inputs Needed",
                *[f"- {item}" for item in payload["next_human_inputs_needed"]],
                "",
                "## Observation-only Caveat",
                payload["observation_only_caveat"],
            ]
        )
    lines.extend(["", "## Safety Summary"])
    lines.extend(_format_safety_summary_lines(payload))
    return "\n".join(lines).rstrip() + "\n"


def write_monthly_portfolio_strategy_outputs(
    *,
    out_dir: Path,
    report_month: str,
    stem: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    monthly = out_dir / "monthly" / report_month
    latest.mkdir(parents=True, exist_ok=True)
    monthly.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("monthly", monthly)):
        md_path = root / f"{stem}.md"
        json_path = root / f"{stem}.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_monthly_portfolio_strategy_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_{stem}_md"] = md_path
        paths[f"{label}_{stem}_json"] = json_path
    return paths
