"""Redacted position snapshot input pack for position-aware DCA review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invis_alpha_os.reports.position_aware_dca_decision_pack import (
    DEFAULT_POSITION_GUARD_SYMBOLS,
    THESIS_BROKEN,
    THESIS_INTACT,
    THESIS_WATCH,
    GenericPositionGuardInput,
    PositionSnapshot,
    build_dca_decision_matrix,
    build_generic_position_guard,
    build_position_aware_dca_decision_pack,
    starter_position_profiles,
    validate_position_snapshot,
)

REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "report_date",
    "portfolio_snapshot_date",
    "currency",
    "cash_buffer_status",
    "household_risk_budget_note",
    "positions",
)

REQUIRED_POSITION_FIELDS: tuple[str, ...] = (
    "symbol",
    "display_name",
    "asset_class",
    "market",
    "account_alias",
    "account_type",
    "shares",
    "average_cost",
    "manual_current_price",
    "market_value",
    "unrealized_pl",
    "unrealized_pl_pct",
    "position_weight_pct",
    "portfolio_weight_pct",
    "sector_tag",
    "theme_tag",
    "cash_buffer_status",
    "thesis_status",
    "business_value_status",
    "valuation_status",
    "technical_status",
    "portfolio_permission_status",
    "dca_policy_mode",
    "max_additional_buy_amount",
    "max_position_weight_pct",
    "must_not_buy_if",
    "review_triggers",
    "operator_notes",
)

ALLOWED_ACCOUNT_TYPES: tuple[str, ...] = ("taxable", "nisa", "spouse_taxable", "spouse_nisa", "watchlist")
ALLOWED_THESIS_STATUS: tuple[str, ...] = (THESIS_INTACT, THESIS_WATCH, THESIS_BROKEN)
ALLOWED_CASH_BUFFER_STATUS: tuple[str, ...] = ("sufficient", "tight", "insufficient", "unknown")
NUMERIC_POSITION_FIELDS: tuple[str, ...] = (
    "shares",
    "average_cost",
    "manual_current_price",
    "market_value",
    "unrealized_pl",
    "unrealized_pl_pct",
    "position_weight_pct",
    "portfolio_weight_pct",
    "max_additional_buy_amount",
    "max_position_weight_pct",
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
    "order_id",
    "trade_id",
    "execution_id",
    "raw_export",
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
    "place order",
    "execute order",
    "market order",
    "limit order",
    "broker login",
    "証券口座番号",
    "成行注文",
    "指値注文",
    "発注する",
)

CONSISTENCY_TOLERANCE_ABS = 2.0
CONSISTENCY_TOLERANCE_PCT = 0.25


def _parse_symbols(symbols_csv: str) -> list[str]:
    return [part.strip() for part in symbols_csv.split(",") if part.strip()]


def _as_float(value: Any, *, field: str) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def detect_forbidden_fields(snapshot: dict[str, Any]) -> tuple[str, ...]:
    hits: set[str] = set()
    for path, _value in _walk_fields(snapshot):
        leaf = path.split(".")[-1].lower()
        for token in FORBIDDEN_FIELD_TOKENS:
            if token in leaf:
                hits.add(path)
                break
    return tuple(sorted(hits))


def detect_forbidden_values(snapshot: dict[str, Any]) -> tuple[str, ...]:
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


def build_redacted_position_snapshot_template(
    *,
    report_date: str,
    symbols_csv: str = DEFAULT_POSITION_GUARD_SYMBOLS,
) -> dict[str, Any]:
    profiles = starter_position_profiles()
    positions: list[dict[str, Any]] = []
    for symbol in _parse_symbols(symbols_csv):
        profile = profiles.get(symbol, {"display_name": symbol})
        positions.append(
            {
                "symbol": symbol,
                "display_name": profile["display_name"],
                "asset_class": "equity",
                "market": "manual_market",
                "account_alias": "taxable_alias_1",
                "account_type": "taxable",
                "shares": 0,
                "average_cost": 0,
                "manual_current_price": 0,
                "market_value": 0,
                "unrealized_pl": 0,
                "unrealized_pl_pct": 0,
                "position_weight_pct": 0,
                "portfolio_weight_pct": 0,
                "sector_tag": "manual_sector_tag",
                "theme_tag": "manual_theme_tag",
                "cash_buffer_status": "unknown",
                "thesis_status": THESIS_WATCH,
                "business_value_status": "unknown",
                "valuation_status": "unknown",
                "technical_status": "needs_current_review",
                "portfolio_permission_status": "manual_review_required",
                "dca_policy_mode": "review_only",
                "max_additional_buy_amount": 0,
                "max_position_weight_pct": 5,
                "must_not_buy_if": [
                    "thesis_status is broken",
                    "portfolio_weight_pct would exceed max_position_weight_pct",
                    "cash_buffer_status is insufficient",
                ],
                "review_triggers": [
                    "price weakness continues",
                    "earnings guidance changes",
                    "dividend sustainability changes",
                ],
                "operator_notes": "human-redacted notes only; no account numbers, order IDs, or broker exports",
            }
        )
    return {
        "pack_version": "v76",
        "report_name": "redacted_position_snapshot_template",
        "source_only": True,
        "report_date": report_date,
        "redacted_snapshot_template": {
            "report_date": report_date,
            "portfolio_snapshot_date": report_date,
            "currency": "JPY",
            "cash_buffer_status": "unknown",
            "household_risk_budget_note": "redacted household allocation note",
            "positions": positions,
        },
        "forbidden_fields_checklist": (
            "broker account numbers",
            "login IDs, passwords, tokens, API keys, secrets",
            "raw broker export columns or files",
            "order IDs, trade IDs, execution IDs",
            "trade execution instructions",
        ),
        "copy_ready_chatgpt_prompt": (
            "このredacted position snapshotを使い、任意銘柄ごとにcheap_price、business_value_status、"
            "thesis_status、portfolio_permission_status、cash_buffer_status、must_not_buy_ifを分けて、"
            "観測・待機・追加検討ブロック条件を整理してください。売買指示は出さないでください。"
        ),
        "safety_summary": _safety_summary(),
    }


def _position_missing_fields(position: dict[str, Any]) -> tuple[str, ...]:
    return tuple(field for field in REQUIRED_POSITION_FIELDS if field not in position)


def _top_missing_fields(snapshot: dict[str, Any]) -> tuple[str, ...]:
    return tuple(field for field in REQUIRED_TOP_LEVEL_FIELDS if field not in snapshot)


def _numerical_consistency(position: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    checks: list[dict[str, Any]] = []
    shares = _as_float(position.get("shares"), field="shares")
    average_cost = _as_float(position.get("average_cost"), field="average_cost")
    price = _as_float(position.get("manual_current_price"), field="manual_current_price")
    market_value = _as_float(position.get("market_value"), field="market_value")
    unrealized_pl = _as_float(position.get("unrealized_pl"), field="unrealized_pl")
    unrealized_pl_pct = _as_float(position.get("unrealized_pl_pct"), field="unrealized_pl_pct")
    if shares is not None and price is not None and market_value is not None:
        expected = shares * price
        checks.append(
            {
                "check": "market_value_equals_shares_times_manual_current_price",
                "pass": abs(market_value - expected) <= max(CONSISTENCY_TOLERANCE_ABS, expected * 0.001),
                "expected": expected,
                "actual": market_value,
            }
        )
    if shares is not None and average_cost is not None and price is not None and unrealized_pl is not None:
        expected = (price - average_cost) * shares
        checks.append(
            {
                "check": "unrealized_pl_matches_price_minus_average_cost",
                "pass": abs(unrealized_pl - expected) <= max(CONSISTENCY_TOLERANCE_ABS, abs(expected) * 0.001),
                "expected": expected,
                "actual": unrealized_pl,
            }
        )
    if average_cost not in (None, 0) and price is not None and unrealized_pl_pct is not None:
        expected = ((price / average_cost) - 1.0) * 100.0
        checks.append(
            {
                "check": "unrealized_pl_pct_matches_price_over_average_cost",
                "pass": abs(unrealized_pl_pct - expected) <= CONSISTENCY_TOLERANCE_PCT,
                "expected": round(expected, 4),
                "actual": unrealized_pl_pct,
            }
        )
    return tuple(checks)


def _position_dca_blockers(position: dict[str, Any], *, cash_buffer_status: str) -> tuple[str, ...]:
    blockers: list[str] = []
    thesis = str(position.get("thesis_status", "")).strip()
    position_cash_status = str(position.get("cash_buffer_status") or cash_buffer_status).strip()
    weight = _as_float(position.get("position_weight_pct", position.get("portfolio_weight_pct")), field="position_weight_pct")
    max_weight = _as_float(position.get("max_position_weight_pct"), field="max_position_weight_pct")
    max_add = _as_float(position.get("max_additional_buy_amount"), field="max_additional_buy_amount")
    if thesis == THESIS_BROKEN:
        blockers.append("thesis_broken")
    if weight is not None and max_weight is not None and weight >= max_weight:
        blockers.append("over_position_limit")
    if position_cash_status in {"insufficient", "unknown"}:
        blockers.append("cash_buffer_not_confirmed")
    if max_add is not None and max_add <= 0:
        blockers.append("max_additional_buy_amount_not_positive")
    return tuple(blockers)


def validate_redacted_position_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    top_missing = _top_missing_fields(snapshot)
    forbidden_fields = detect_forbidden_fields(snapshot)
    forbidden_values = detect_forbidden_values(snapshot)
    positions_value = snapshot.get("positions")
    positions = positions_value if isinstance(positions_value, list) else []
    position_results: list[dict[str, Any]] = []
    cash_status = str(snapshot.get("cash_buffer_status", "")).strip()
    top_errors: list[str] = []
    if cash_status and cash_status not in ALLOWED_CASH_BUFFER_STATUS:
        top_errors.append("cash_buffer_status_invalid")
    if not isinstance(positions_value, list):
        top_errors.append("positions_must_be_list")

    for index, position in enumerate(positions):
        if not isinstance(position, dict):
            position_results.append(
                {
                    "index": index,
                    "symbol": None,
                    "valid": False,
                    "missing_fields": REQUIRED_POSITION_FIELDS,
                    "field_errors": ("position_must_be_object",),
                    "numerical_consistency": (),
                    "dca_readiness_blockers": (),
                    "chatgpt_paste_ready": False,
                }
            )
            continue
        missing = _position_missing_fields(position)
        field_errors: list[str] = []
        account_type = str(position.get("account_type", "")).strip()
        thesis_status = str(position.get("thesis_status", "")).strip()
        if account_type and account_type not in ALLOWED_ACCOUNT_TYPES:
            field_errors.append("account_type_invalid")
        if thesis_status and thesis_status not in ALLOWED_THESIS_STATUS:
            field_errors.append("thesis_status_invalid")
        for field in NUMERIC_POSITION_FIELDS:
            if field in position and _as_float(position[field], field=field) is None:
                field_errors.append(f"{field}_not_numeric")
        consistency = _numerical_consistency(position)
        consistency_failed = tuple(row for row in consistency if not row["pass"])
        blockers = _position_dca_blockers(position, cash_buffer_status=cash_status)
        valid = not missing and not field_errors and not consistency_failed
        position_results.append(
            {
                "index": index,
                "symbol": position.get("symbol"),
                "valid": valid,
                "missing_fields": missing,
                "field_errors": tuple(field_errors),
                "numerical_consistency": consistency,
                "dca_readiness_blockers": blockers,
                "chatgpt_paste_ready": valid and not forbidden_fields and not forbidden_values,
            }
        )

    valid_positions = bool(position_results) and all(row["valid"] for row in position_results)
    validation_passed = (
        not top_missing
        and not top_errors
        and not forbidden_fields
        and not forbidden_values
        and valid_positions
    )
    return {
        "pack_version": "v76",
        "report_name": "redacted_position_snapshot_validation",
        "source_only": True,
        "validation_passed": validation_passed,
        "top_level_missing_fields": top_missing,
        "top_level_errors": tuple(top_errors),
        "forbidden_fields_detected": forbidden_fields,
        "forbidden_values_detected": forbidden_values,
        "position_results": tuple(position_results),
        "chatgpt_paste_ready": validation_passed,
        "dca_readiness_blockers": tuple(
            sorted({blocker for row in position_results for blocker in row["dca_readiness_blockers"]})
        ),
        "safety_summary": _safety_summary(),
    }


def load_redacted_position_snapshot_json(path: Path) -> dict[str, Any]:
    """Load a human-created redacted JSON snapshot.

    This intentionally supports only JSON redacted snapshots. It is not a raw
    broker export parser and does not normalize broker statements.
    """

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("redacted position snapshot JSON must be an object")
    return data


def _snapshot_to_v74_position(position: dict[str, Any], *, cash_buffer_status: str) -> PositionSnapshot:
    max_add = _as_float(position.get("max_additional_buy_amount"), field="max_additional_buy_amount") or 0.0
    remaining_cash = max_add if cash_buffer_status == "sufficient" else 0.0
    weight = position.get("position_weight_pct", position.get("portfolio_weight_pct"))
    return validate_position_snapshot(
        {
            "symbol": position["symbol"],
            "display_name": position["display_name"],
            "account_label": position["account_alias"],
            "shares": position["shares"],
            "average_cost": position["average_cost"],
            "last_price": position["manual_current_price"],
            "market_value": position["market_value"],
            "unrealized_pnl": position["unrealized_pl"],
            "unrealized_pnl_pct": position["unrealized_pl_pct"],
            "portfolio_weight_pct": weight,
            "sector_weight_pct": 0,
            "intended_role": position.get("dca_policy_mode", position.get("dca_intent", "review_only")),
            "max_position_weight_pct": position["max_position_weight_pct"],
            "planned_dca_budget": max_add,
            "remaining_cash_buffer": remaining_cash,
        }
    )


def _position_to_generic_guard_input(position: dict[str, Any], *, top_cash_buffer_status: str) -> GenericPositionGuardInput:
    return GenericPositionGuardInput(
        symbol=str(position["symbol"]),
        display_name=str(position["display_name"]),
        asset_class=str(position["asset_class"]),
        market=str(position["market"]),
        sector_tag=str(position["sector_tag"]),
        theme_tag=str(position["theme_tag"]),
        position_weight_pct=_as_float(
            position.get("position_weight_pct", position.get("portfolio_weight_pct")),
            field="position_weight_pct",
        )
        or 0.0,
        max_position_weight_pct=_as_float(position.get("max_position_weight_pct"), field="max_position_weight_pct")
        or 0.0,
        cash_buffer_status=str(position.get("cash_buffer_status") or top_cash_buffer_status),
        thesis_status=str(position["thesis_status"]),
        business_value_status=str(position["business_value_status"]),
        valuation_status=str(position["valuation_status"]),
        technical_status=str(position["technical_status"]),
        portfolio_permission_status=str(position["portfolio_permission_status"]),
        dca_policy_mode=str(position["dca_policy_mode"]),
        max_additional_buy_amount=_as_float(
            position.get("max_additional_buy_amount"),
            field="max_additional_buy_amount",
        )
        or 0.0,
        must_not_buy_if=tuple(str(item) for item in position.get("must_not_buy_if", ())),
        review_triggers=tuple(str(item) for item in position.get("review_triggers", ())),
        operator_notes=str(position.get("operator_notes", "")),
    )


def build_redacted_position_strategy_pack(
    *,
    report_date: str,
    redacted_snapshot: dict[str, Any] | None = None,
    symbols_csv: str = DEFAULT_POSITION_GUARD_SYMBOLS,
) -> dict[str, Any]:
    snapshot = redacted_snapshot or build_redacted_position_snapshot_template(
        report_date=report_date,
        symbols_csv=symbols_csv,
    )["redacted_snapshot_template"]
    validation = validate_redacted_position_snapshot(snapshot)
    snapshot_symbols_csv = ",".join(str(row.get("symbol", "")) for row in snapshot.get("positions", ()))
    placeholder_pack = build_position_aware_dca_decision_pack(
        report_date=report_date,
        symbols_csv=snapshot_symbols_csv or symbols_csv,
    )
    placeholder_by_symbol = {
        row["symbol"]: row["dca_decision_matrix"]["decision_label"] for row in placeholder_pack["rows"]
    }
    profiles = starter_position_profiles()
    rows: list[dict[str, Any]] = []
    if validation["validation_passed"]:
        for position in snapshot["positions"]:
            symbol = str(position["symbol"])
            profile = profiles.get(symbol, {"starter_tags": {}})
            tags = profile.get("starter_tags", {})
            v74_position = _snapshot_to_v74_position(position, cash_buffer_status=str(snapshot["cash_buffer_status"]))
            matrix = build_dca_decision_matrix(
                snapshot=v74_position,
                valuation_tags=tuple(tags.get("valuation", ())),
                trend_tags=tuple(tags.get("trend", ())),
                business_risk_tags=tuple(tags.get("business_risk", ())),
                dividend_tags=tuple(tags.get("dividend", ())),
                thesis_integrity_status=str(position["thesis_status"]),
            )
            generic_guard = build_generic_position_guard(
                _position_to_generic_guard_input(
                    position,
                    top_cash_buffer_status=str(snapshot["cash_buffer_status"]),
                )
            )
            rows.append(
                {
                    "symbol": symbol,
                    "display_name": position["display_name"],
                    "starter_fixture_label": placeholder_by_symbol.get(symbol, "not_available"),
                    "redacted_position_label": matrix["decision_label"],
                    "generic_guard_label": generic_guard["guard_label"],
                    "portfolio_weight_pct": position["portfolio_weight_pct"],
                    "position_weight_pct": position["position_weight_pct"],
                    "max_position_weight_pct": position["max_position_weight_pct"],
                    "cash_buffer_status": position.get("cash_buffer_status") or snapshot["cash_buffer_status"],
                    "thesis_status": position["thesis_status"],
                    "dca_readiness_blockers": validation["dca_readiness_blockers"],
                    "matrix": matrix,
                    "generic_guard": generic_guard,
                }
            )
    return {
        "pack_version": "v76",
        "report_name": "redacted_position_strategy_pack",
        "source_only": True,
        "report_date": report_date,
        "validation": validation,
        "rows": tuple(rows),
        "strategy_summary": {
            "chatgpt_paste_ready": validation["chatgpt_paste_ready"],
            "one_page_summary": "redacted position-aware strategy dialogue pack; observation-only; no trade instruction",
            "household_allocation_caveat": snapshot.get("household_risk_budget_note"),
        },
        "safety_summary": _safety_summary(),
    }


def build_redacted_position_human_input_checklist(
    *,
    report_date: str,
    symbols_csv: str = DEFAULT_POSITION_GUARD_SYMBOLS,
) -> dict[str, Any]:
    return {
        "pack_version": "v76",
        "report_name": "redacted_position_human_input_checklist",
        "source_only": True,
        "report_date": report_date,
        "symbols": tuple(_parse_symbols(symbols_csv)),
        "required_inputs": (
            "portfolio_snapshot_date",
            "cash_buffer_status",
            "household_risk_budget_note",
            "asset_class",
            "market",
            "shares",
            "average_cost",
            "manual_current_price",
            "position_weight_pct",
            "portfolio_weight_pct",
            "thesis_status",
            "business_value_status",
            "valuation_status",
            "technical_status",
            "portfolio_permission_status",
            "dca_policy_mode",
            "max_additional_buy_amount",
            "max_position_weight_pct",
            "must_not_buy_if",
            "review_triggers",
        ),
        "do_not_include": (
            "broker account number",
            "login ID, password, token, API key, secret",
            "raw broker CSV/export rows",
            "order ID, trade ID, execution ID",
            "market/limit order instructions",
            "screenshots or raw statements",
        ),
        "operator_sequence": (
            "generate template with position-snapshot-template",
            "fill only redacted manual values",
            "validate with position-snapshot-validate",
            "generate ChatGPT strategy pack with position-aware-dca-strategy-pack",
            "use ChatGPT for scenario review only; do not treat output as order instruction",
        ),
        "safety_summary": _safety_summary(),
    }


def _safety_summary() -> dict[str, bool]:
    return {
        "provider_live_access_executed": False,
        "live_http_executed": False,
        "cache_write_executed": False,
        "actual_refresh_import_executed": False,
        "manual_actual_import_executed": False,
        "broker_api_access_executed": False,
        "broker_login_executed": False,
        "raw_broker_export_parsed": False,
        "raw_broker_data_persisted": False,
        "raw_ohlcv_api_persistence_executed": False,
        "reports_private_raw_data_written": False,
        "git_tracked_raw_data_written": False,
        "env_secret_displayed": False,
        "workflow_files_modified": False,
        "dependency_pyproject_changed": False,
        "trading_action_executed": False,
        "order_placement_executed": False,
    }


def format_redacted_position_snapshot_template_markdown(payload: dict[str, Any]) -> str:
    template = payload["redacted_snapshot_template"]
    lines = [
        "# Redacted Position Snapshot Template v76",
        "",
        "This template is for manual redacted input only. Do not paste broker account numbers, raw broker exports, secrets, or order instructions.",
        "",
        "## JSON Skeleton",
        "```json",
        json.dumps(template, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Forbidden Fields Checklist",
    ]
    lines.extend(f"- {item}" for item in payload["forbidden_fields_checklist"])
    lines.extend(
        [
            "",
            "## Copy-ready ChatGPT Prompt",
            "```text",
            payload["copy_ready_chatgpt_prompt"],
            "```",
            "",
            "## Safety Summary",
        ]
    )
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_redacted_position_snapshot_validation_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Redacted Position Snapshot Validation v76",
        "",
        f"- validation_passed: {str(payload['validation_passed']).lower()}",
        f"- chatgpt_paste_ready: {str(payload['chatgpt_paste_ready']).lower()}",
        f"- top_level_missing_fields: {', '.join(payload['top_level_missing_fields']) if payload['top_level_missing_fields'] else 'none'}",
        f"- forbidden_fields_detected: {', '.join(payload['forbidden_fields_detected']) if payload['forbidden_fields_detected'] else 'none'}",
        f"- forbidden_values_detected: {', '.join(payload['forbidden_values_detected']) if payload['forbidden_values_detected'] else 'none'}",
        f"- dca_readiness_blockers: {', '.join(payload['dca_readiness_blockers']) if payload['dca_readiness_blockers'] else 'none'}",
        "",
        "## Position Results",
        "| symbol | valid | missing_fields | field_errors | chatgpt_paste_ready |",
        "|---|---|---|---|---|",
    ]
    for row in payload["position_results"]:
        lines.append(
            f"| {row['symbol']} | {str(row['valid']).lower()} | "
            f"{', '.join(row['missing_fields']) if row['missing_fields'] else 'none'} | "
            f"{', '.join(row['field_errors']) if row['field_errors'] else 'none'} | "
            f"{str(row['chatgpt_paste_ready']).lower()} |"
        )
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_redacted_position_strategy_pack_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Redacted Position Strategy Pack v76",
        "",
        "Observation-only strategy dialogue pack. This is not a trading recommendation or order instruction.",
        "",
        "## Strategy Summary",
        f"- chatgpt_paste_ready: {str(payload['strategy_summary']['chatgpt_paste_ready']).lower()}",
        f"- household_allocation_caveat: {payload['strategy_summary']['household_allocation_caveat']}",
        "",
        "## Generic Position Guard",
        "| symbol | starter_fixture_label | redacted_position_label | generic_guard_label | position_weight_pct | max_position_weight_pct | cash_buffer_status | thesis_status |",
        "|---|---|---|---|---:|---:|---|---|",
    ]
    if payload["rows"]:
        for row in payload["rows"]:
            lines.append(
                f"| {row['symbol']} | {row['starter_fixture_label']} | {row['redacted_position_label']} | "
                f"{row['generic_guard_label']} | {row['position_weight_pct']} | {row['max_position_weight_pct']} | "
                f"{row['cash_buffer_status']} | {row['thesis_status']} |"
            )
    else:
        lines.append("| not_ready | not_available | validation_required | validation_required | 0 | 0 | unknown | unknown |")
    lines.extend(
        [
            "",
            "## Average-Down Permission Matrix",
            "- price decline alone is insufficient",
            "- business value improvement must be separately confirmed",
            "- thesis_status must remain intact before any add discussion",
            "- cash buffer and max position weight must permit additional exposure",
            "- starter examples are fixtures only; no symbol-specific guard branch is used",
            "",
            "## Copy-ready ChatGPT Prompt",
            "```text",
            "このredacted position strategy packを使い、任意銘柄のgeneric_guard_label、cash buffer、",
            "portfolio weight、max position weight、thesis_status、must-not-buy条件を分けて、",
            "追加・待機・縮小レビューの論点を整理してください。売買指示は出さないでください。",
            "```",
            "",
            "## Safety Summary",
        ]
    )
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_redacted_position_human_input_checklist_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Redacted Position Human Input Checklist v76",
        "",
        "Use this checklist before filling generic redacted position snapshots for any symbol.",
        "",
        f"- report_date: {payload['report_date']}",
        f"- symbols: {', '.join(payload['symbols'])}",
        "",
        "## Required Inputs",
    ]
    lines.extend(f"- {item}" for item in payload["required_inputs"])
    lines.extend(["", "## Do Not Include"])
    lines.extend(f"- {item}" for item in payload["do_not_include"])
    lines.extend(["", "## Operator Sequence"])
    lines.extend(f"- {item}" for item in payload["operator_sequence"])
    lines.extend(["", "## Safety Summary"])
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_redacted_position_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_redacted_position_outputs(
    *,
    out_dir: Path,
    report_date: str,
    stem: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    dated = out_dir / report_date
    latest.mkdir(parents=True, exist_ok=True)
    dated.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("dated", dated)):
        md_path = root / f"{stem}.md"
        json_path = root / f"{stem}.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_redacted_position_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_{stem}_md"] = md_path
        paths[f"{label}_{stem}_json"] = json_path
    return paths
