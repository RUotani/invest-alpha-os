"""Position-aware DCA decision pack for redacted manual snapshots.

This module is source-only. It does not read broker exports, call providers,
write cache, place orders, or emit trading instructions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


DCA_DECISION_LABELS = (
    "no_action",
    "monitor_only",
    "small_add_allowed",
    "staged_add_allowed",
    "wait_for_capitulation",
    "reduce_or_stop_loss_review",
)

DcaDecisionLabel = Literal[
    "no_action",
    "monitor_only",
    "small_add_allowed",
    "staged_add_allowed",
    "wait_for_capitulation",
    "reduce_or_stop_loss_review",
]

THESIS_INTACT = "intact"
THESIS_WATCH = "watch"
THESIS_BROKEN = "broken"


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    display_name: str
    account_label: str
    shares: float
    average_cost: float
    last_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    portfolio_weight_pct: float
    sector_weight_pct: float
    intended_role: str
    max_position_weight_pct: float
    planned_dca_budget: float
    remaining_cash_buffer: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "display_name": self.display_name,
            "account_label": self.account_label,
            "shares": self.shares,
            "average_cost": self.average_cost,
            "last_price": self.last_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
            "portfolio_weight_pct": self.portfolio_weight_pct,
            "sector_weight_pct": self.sector_weight_pct,
            "intended_role": self.intended_role,
            "max_position_weight_pct": self.max_position_weight_pct,
            "planned_dca_budget": self.planned_dca_budget,
            "remaining_cash_buffer": self.remaining_cash_buffer,
        }


def _as_float(value: Any, *, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    return number


def _as_non_empty_string(value: Any, *, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _validate_non_negative(number: float, *, field: str) -> None:
    if number < 0:
        raise ValueError(f"{field} must be non-negative")


def validate_position_snapshot(raw: dict[str, Any]) -> PositionSnapshot:
    """Validate a redacted manual position snapshot.

    The contract intentionally accepts JP symbols such as ``285A.T`` and does
    not assume four-digit-only ticker normalization.
    """

    required = (
        "symbol",
        "display_name",
        "account_label",
        "shares",
        "average_cost",
        "last_price",
        "market_value",
        "unrealized_pnl",
        "unrealized_pnl_pct",
        "portfolio_weight_pct",
        "sector_weight_pct",
        "intended_role",
        "max_position_weight_pct",
        "planned_dca_budget",
        "remaining_cash_buffer",
    )
    missing = [field for field in required if field not in raw]
    if missing:
        raise ValueError(f"missing position snapshot fields: {', '.join(missing)}")

    symbol = _as_non_empty_string(raw["symbol"], field="symbol")
    display_name = _as_non_empty_string(raw["display_name"], field="display_name")
    account_label = _as_non_empty_string(raw["account_label"], field="account_label")
    intended_role = _as_non_empty_string(raw["intended_role"], field="intended_role")
    shares = _as_float(raw["shares"], field="shares")
    average_cost = _as_float(raw["average_cost"], field="average_cost")
    last_price = _as_float(raw["last_price"], field="last_price")
    market_value = _as_float(raw["market_value"], field="market_value")
    unrealized_pnl = _as_float(raw["unrealized_pnl"], field="unrealized_pnl")
    unrealized_pnl_pct = _as_float(raw["unrealized_pnl_pct"], field="unrealized_pnl_pct")
    portfolio_weight_pct = _as_float(raw["portfolio_weight_pct"], field="portfolio_weight_pct")
    sector_weight_pct = _as_float(raw["sector_weight_pct"], field="sector_weight_pct")
    max_position_weight_pct = _as_float(raw["max_position_weight_pct"], field="max_position_weight_pct")
    planned_dca_budget = _as_float(raw["planned_dca_budget"], field="planned_dca_budget")
    remaining_cash_buffer = _as_float(raw["remaining_cash_buffer"], field="remaining_cash_buffer")

    for field, number in (
        ("shares", shares),
        ("average_cost", average_cost),
        ("last_price", last_price),
        ("market_value", market_value),
        ("portfolio_weight_pct", portfolio_weight_pct),
        ("sector_weight_pct", sector_weight_pct),
        ("max_position_weight_pct", max_position_weight_pct),
        ("planned_dca_budget", planned_dca_budget),
        ("remaining_cash_buffer", remaining_cash_buffer),
    ):
        _validate_non_negative(number, field=field)
    if max_position_weight_pct <= 0:
        raise ValueError("max_position_weight_pct must be positive")

    return PositionSnapshot(
        symbol=symbol,
        display_name=display_name,
        account_label=account_label,
        shares=shares,
        average_cost=average_cost,
        last_price=last_price,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        portfolio_weight_pct=portfolio_weight_pct,
        sector_weight_pct=sector_weight_pct,
        intended_role=intended_role,
        max_position_weight_pct=max_position_weight_pct,
        planned_dca_budget=planned_dca_budget,
        remaining_cash_buffer=remaining_cash_buffer,
    )


def jfe_honda_starter_profiles() -> dict[str, dict[str, Any]]:
    return {
        "5411.T": {
            "symbol": "5411.T",
            "display_name": "JFE Holdings",
            "investment_thesis": (
                "cyclical recovery and shareholder return candidate, subject to steel-cycle and balance-sheet risk"
            ),
            "valuation_context": (
                "low valuation or high dividend appearance must be tested against normalized steel margins and payout capacity"
            ),
            "yield_context": "dividend attractiveness is not sufficient without payout sustainability evidence",
            "starter_tags": {
                "valuation": ("cheap_vs_history_needs_normalized_earnings_check",),
                "trend": ("falling_price_manual_review", "cyclical_downturn_sensitive"),
                "business_risk": (
                    "steel_cycle",
                    "domestic_demand_flatness",
                    "china_export_pressure",
                    "raw_material_spread_risk",
                    "leverage_capital_intensity",
                ),
                "dividend": ("dividend_floor_vs_payout_sustainability",),
            },
            "risk_factors": (
                "steel cycle",
                "domestic demand flatness",
                "China/export pressure",
                "raw material spread risk",
                "leverage / capital intensity",
                "dividend floor vs payout sustainability",
            ),
        },
        "7267.T": {
            "symbol": "7267.T",
            "display_name": "Honda Motor",
            "investment_thesis": (
                "global auto and motorcycle value candidate, subject to EV reset, regional competition, and margin pressure"
            ),
            "valuation_context": (
                "low PBR or shareholder return thesis should be separated from near-term auto margin deterioration"
            ),
            "yield_context": "shareholder return support matters, but does not override strategic execution risk",
            "starter_tags": {
                "valuation": ("low_pbr_shareholder_return_thesis",),
                "trend": ("soft_price_manual_review", "auto_cycle_sensitive"),
                "business_risk": (
                    "ev_related_losses_strategic_reset",
                    "us_tariff_sensitivity",
                    "china_asia_competition",
                    "auto_margin_pressure",
                    "motorcycle_segment_offset",
                ),
                "dividend": ("shareholder_return_low_pbr_thesis",),
            },
            "risk_factors": (
                "EV-related losses / strategic reset",
                "US tariff sensitivity",
                "China/Asia competition",
                "auto margin pressure",
                "motorcycle segment offset",
                "shareholder return / low PBR thesis",
            ),
        },
    }


def fixture_position_snapshots() -> dict[str, PositionSnapshot]:
    """Return redacted fixture snapshots for report wiring tests and dry-runs."""

    return {
        "5411.T": validate_position_snapshot(
            {
                "symbol": "5411.T",
                "display_name": "JFE Holdings",
                "account_label": "manual_redacted_fixture_taxable",
                "shares": 100,
                "average_cost": 2300,
                "last_price": 1900,
                "market_value": 190000,
                "unrealized_pnl": -40000,
                "unrealized_pnl_pct": -17.39,
                "portfolio_weight_pct": 2.4,
                "sector_weight_pct": 4.8,
                "intended_role": "cyclical recovery",
                "max_position_weight_pct": 5.0,
                "planned_dca_budget": 50000,
                "remaining_cash_buffer": 400000,
            }
        ),
        "7267.T": validate_position_snapshot(
            {
                "symbol": "7267.T",
                "display_name": "Honda Motor",
                "account_label": "manual_redacted_fixture_taxable",
                "shares": 100,
                "average_cost": 1700,
                "last_price": 1500,
                "market_value": 150000,
                "unrealized_pnl": -20000,
                "unrealized_pnl_pct": -11.76,
                "portfolio_weight_pct": 2.0,
                "sector_weight_pct": 3.5,
                "intended_role": "satellite",
                "max_position_weight_pct": 5.0,
                "planned_dca_budget": 50000,
                "remaining_cash_buffer": 400000,
            }
        ),
        "285A.T": validate_position_snapshot(
            {
                "symbol": "285A.T",
                "display_name": "JP alphanumeric symbol fixture",
                "account_label": "manual_redacted_fixture_taxable",
                "shares": 0,
                "average_cost": 0,
                "last_price": 0,
                "market_value": 0,
                "unrealized_pnl": 0,
                "unrealized_pnl_pct": 0,
                "portfolio_weight_pct": 0,
                "sector_weight_pct": 0,
                "intended_role": "watchlist",
                "max_position_weight_pct": 1.0,
                "planned_dca_budget": 0,
                "remaining_cash_buffer": 0,
            }
        ),
    }


def build_dca_decision_matrix(
    *,
    snapshot: PositionSnapshot,
    valuation_tags: tuple[str, ...] = (),
    trend_tags: tuple[str, ...] = (),
    business_risk_tags: tuple[str, ...] = (),
    dividend_tags: tuple[str, ...] = (),
    thesis_integrity_status: str = THESIS_WATCH,
) -> dict[str, Any]:
    cheaper = snapshot.last_price < snapshot.average_cost if snapshot.average_cost > 0 else False
    business_value_better = "business_value_improving" in valuation_tags or "earnings_revision_positive" in valuation_tags
    thesis_intact = thesis_integrity_status == THESIS_INTACT
    portfolio_risk_permits = snapshot.portfolio_weight_pct < snapshot.max_position_weight_pct
    cash_buffer_sufficient = snapshot.remaining_cash_buffer >= snapshot.planned_dca_budget and snapshot.planned_dca_budget > 0
    dividend_attractive = any("dividend" in tag or "shareholder_return" in tag for tag in dividend_tags)
    high_risk = bool(
        {"leverage_capital_intensity", "auto_margin_pressure", "ev_related_losses_strategic_reset"}.intersection(
            business_risk_tags
        )
    )
    capitulation_risk = "falling_price_manual_review" in trend_tags or "cyclical_downturn_sensitive" in trend_tags

    blockers: list[str] = []
    warnings: list[str] = []
    if snapshot.portfolio_weight_pct >= snapshot.max_position_weight_pct:
        blockers.append("over_position_limit")
    if thesis_integrity_status == THESIS_BROKEN:
        blockers.append("thesis_broken")
    if not cash_buffer_sufficient:
        blockers.append("cash_buffer_insufficient")
    if dividend_attractive and not business_value_better:
        warnings.append("dividend_or_yield_attractiveness_alone_is_insufficient")
    if high_risk:
        warnings.append("business_risk_requires_human_review")
    if capitulation_risk:
        warnings.append("falling_price_requires_capitulation_scenario_review")

    if "thesis_broken" in blockers:
        label: DcaDecisionLabel = "reduce_or_stop_loss_review"
    elif blockers:
        label = "monitor_only"
    elif dividend_attractive and not business_value_better and not valuation_tags:
        label = "monitor_only"
    elif cheaper and thesis_intact and portfolio_risk_permits and cash_buffer_sufficient and business_value_better:
        label = "staged_add_allowed"
    elif cheaper and thesis_intact and portfolio_risk_permits and cash_buffer_sufficient:
        label = "small_add_allowed"
    elif cheaper and capitulation_risk:
        label = "wait_for_capitulation"
    elif not cheaper:
        label = "no_action"
    else:
        label = "monitor_only"

    return {
        "decision_label": label,
        "observation_only_not_trade_instruction": True,
        "price_is_cheaper": cheaper,
        "business_value_is_better": business_value_better,
        "thesis_is_intact": thesis_intact,
        "portfolio_risk_permits_additional_exposure": portfolio_risk_permits,
        "cash_buffer_sufficient": cash_buffer_sufficient,
        "dividend_attractive": dividend_attractive,
        "blockers": tuple(blockers),
        "warnings": tuple(warnings),
        "required_human_checks": (
            "confirm thesis integrity with current filings/news before any action",
            "confirm allocation and cash buffer against household plan",
            "confirm no NISA sell/reduce action is implied by this pack",
        ),
    }


def _parse_symbols(symbols_csv: str) -> list[str]:
    return [part.strip() for part in symbols_csv.split(",") if part.strip()]


def _profile_for_symbol(symbol: str) -> dict[str, Any]:
    profiles = jfe_honda_starter_profiles()
    return profiles.get(
        symbol,
        {
            "symbol": symbol,
            "display_name": symbol,
            "investment_thesis": "manual profile required",
            "valuation_context": "manual valuation context required",
            "yield_context": "manual yield context required",
            "starter_tags": {"valuation": (), "trend": (), "business_risk": (), "dividend": ()},
            "risk_factors": ("manual risk review required",),
        },
    )


def _snapshot_for_symbol(symbol: str) -> PositionSnapshot:
    snapshots = fixture_position_snapshots()
    if symbol in snapshots:
        return snapshots[symbol]
    return validate_position_snapshot(
        {
            "symbol": symbol,
            "display_name": symbol,
            "account_label": "manual_redacted_placeholder",
            "shares": 0,
            "average_cost": 0,
            "last_price": 0,
            "market_value": 0,
            "unrealized_pnl": 0,
            "unrealized_pnl_pct": 0,
            "portfolio_weight_pct": 0,
            "sector_weight_pct": 0,
            "intended_role": "manual_review_required",
            "max_position_weight_pct": 1.0,
            "planned_dca_budget": 0,
            "remaining_cash_buffer": 0,
        }
    )


def build_position_aware_dca_decision_pack(
    *,
    report_date: str,
    symbols_csv: str = "5411.T,7267.T",
) -> dict[str, Any]:
    symbols = _parse_symbols(symbols_csv)
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        profile = _profile_for_symbol(symbol)
        snapshot = _snapshot_for_symbol(symbol)
        tags = profile["starter_tags"]
        matrix = build_dca_decision_matrix(
            snapshot=snapshot,
            valuation_tags=tuple(tags.get("valuation", ())),
            trend_tags=tuple(tags.get("trend", ())),
            business_risk_tags=tuple(tags.get("business_risk", ())),
            dividend_tags=tuple(tags.get("dividend", ())),
            thesis_integrity_status=THESIS_WATCH,
        )
        rows.append(
            {
                "symbol": symbol,
                "position_snapshot": snapshot.to_dict(),
                "profile": profile,
                "dca_decision_matrix": matrix,
                "what_has_changed": (
                    "user observed price weakness; current business/news confirmation is missing in source-only pack"
                ),
                "missing_data": (
                    "current price source confirmation",
                    "latest earnings and guidance",
                    "dividend sustainability evidence",
                    "household allocation target",
                    "actual redacted position snapshot if fixture values are insufficient",
                ),
            }
        )

    return {
        "pack_version": "v74",
        "report_name": "position_aware_dca_decision_pack",
        "source_only": True,
        "report_date": report_date,
        "symbols": symbols,
        "rows": tuple(rows),
        "chatgpt_usage_boundary": {
            "intended_use": "strategy_dialogue_with_redacted_summary",
            "not_investment_advice": True,
            "not_trade_instruction": True,
            "raw_broker_data_allowed": False,
            "raw_provider_data_allowed": False,
        },
        "safety_summary": {
            "provider_live_access_executed": False,
            "live_http_executed": False,
            "cache_write_executed": False,
            "actual_refresh_import_executed": False,
            "manual_actual_import_executed": False,
            "broker_api_access_executed": False,
            "raw_broker_export_parsed": False,
            "raw_ohlcv_persistence_executed": False,
            "raw_api_response_persistence_executed": False,
            "env_secret_displayed": False,
            "workflow_files_modified": False,
            "dependency_pyproject_changed": False,
            "trading_action_executed": False,
        },
    }


def format_position_aware_dca_decision_pack_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Position-Aware DCA Decision Pack v74",
        "",
        "注意書き: 投資助言ではなく、観測・検証・ChatGPT対話用のredacted summaryです。",
        "売買推奨・発注指示・broker automationではありません。",
        "",
        "## Pack Summary",
        f"- report_date: {payload['report_date']}",
        f"- symbols: {', '.join(payload['symbols'])}",
        f"- source_only: {str(payload['source_only']).lower()}",
        "",
    ]
    for row in payload["rows"]:
        snapshot = row["position_snapshot"]
        profile = row["profile"]
        matrix = row["dca_decision_matrix"]
        lines.extend(
            [
                f"## {row['symbol']} — {profile['display_name']}",
                "",
                "### Position Snapshot Summary",
                f"- account_label: {snapshot['account_label']}",
                f"- shares: {snapshot['shares']}",
                f"- average_cost: {snapshot['average_cost']}",
                f"- last_price: {snapshot['last_price']}",
                f"- unrealized_pnl_pct: {snapshot['unrealized_pnl_pct']}",
                f"- portfolio_weight_pct: {snapshot['portfolio_weight_pct']}",
                f"- max_position_weight_pct: {snapshot['max_position_weight_pct']}",
                f"- planned_dca_budget: {snapshot['planned_dca_budget']}",
                f"- remaining_cash_buffer: {snapshot['remaining_cash_buffer']}",
                "",
                "### Investment Thesis",
                f"- {profile['investment_thesis']}",
                "",
                "### What Has Changed",
                f"- {row['what_has_changed']}",
                "",
                "### Valuation / Yield Context",
                f"- valuation: {profile['valuation_context']}",
                f"- yield: {profile['yield_context']}",
                "",
                "### Technical / Momentum Context",
                "- source-only placeholder; confirm trend, support/resistance, and capitulation signs before any action.",
                "",
                "### DCA Decision Matrix",
                f"- decision_label: {matrix['decision_label']}",
                f"- price_is_cheaper: {str(matrix['price_is_cheaper']).lower()}",
                f"- business_value_is_better: {str(matrix['business_value_is_better']).lower()}",
                f"- thesis_is_intact: {str(matrix['thesis_is_intact']).lower()}",
                f"- portfolio_risk_permits_additional_exposure: {str(matrix['portfolio_risk_permits_additional_exposure']).lower()}",
                f"- cash_buffer_sufficient: {str(matrix['cash_buffer_sufficient']).lower()}",
                f"- blockers: {', '.join(matrix['blockers']) if matrix['blockers'] else 'none'}",
                f"- warnings: {', '.join(matrix['warnings']) if matrix['warnings'] else 'none'}",
                "",
                "### Risk Gates",
            ]
        )
        lines.extend(f"- {risk}" for risk in profile["risk_factors"])
        lines.extend(["", "### Missing Data"])
        lines.extend(f"- {item}" for item in row["missing_data"])
        lines.extend(
            [
                "",
                "### Questions for User",
                "- この銘柄の投資仮説は現在も成立していますか?",
                "- 追加投入後のportfolio_weight_pctはmax_position_weight_pctを超えませんか?",
                "- 配当利回り以外にbusiness value改善を示す根拠はありますか?",
                "",
            ]
        )

    lines.extend(
        [
            "## Copy-ready ChatGPT Prompt",
            "```text",
            "以下はsource-onlyのredacted position-aware DCA summaryです。",
            "売買指示ではなく、JFE/Hondaの平均取得単価、含み損益、portfolio weight、cash buffer、",
            "投資仮説の健全性、事業リスク、配当持続性を分けて、追加・待機・縮小レビューの論点を整理してください。",
            "特に『価格が安い』と『事業価値が改善した』を混同しないでください。",
            "```",
            "",
            "## Safety Summary",
        ]
    )
    for key, value in payload["safety_summary"].items():
        lines.append(f"- {key}: {str(value).lower()}")
    return "\n".join(lines).rstrip() + "\n"


def format_position_aware_dca_decision_pack_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_position_aware_dca_decision_pack_outputs(
    *,
    out_dir: Path,
    report_date: str,
    markdown_text: str,
    json_payload: dict[str, Any],
) -> dict[str, Path]:
    latest = out_dir / "latest"
    dated = out_dir / report_date
    latest.mkdir(parents=True, exist_ok=True)
    dated.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for label, root in (("latest", latest), ("dated", dated)):
        md_path = root / "position_aware_dca_decision_pack.md"
        json_path = root / "position_aware_dca_decision_pack.json"
        md_path.write_text(markdown_text, encoding="utf-8")
        json_path.write_text(format_position_aware_dca_decision_pack_json(json_payload) + "\n", encoding="utf-8")
        paths[f"{label}_position_aware_dca_decision_pack_md"] = md_path
        paths[f"{label}_position_aware_dca_decision_pack_json"] = json_path
    return paths
