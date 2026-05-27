"""Weekly Observation Report v1 — single read-only report for human MERGE/STOP judgment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.product.portfolio_readiness import evaluate_portfolio_readiness
from invis_alpha_os.product.post_p10_refresh_smoke import build_post_refresh_hints_light
from invis_alpha_os.product.risk_veto_observation_summary import (
    format_risk_veto_observation_summary_markdown,
    summarize_risk_veto_observation_log,
)
from invis_alpha_os.product.us_forward_return_validation import THIN_SAMPLE_THRESHOLD
from invis_alpha_os.product.weekly_us_observation import (
    WeeklyUsObservationResult,
    format_weekly_us_observation_markdown,
    run_weekly_us_observation_cycle,
)

P3_MONITORING_GATE_HEADLINE = (
    "P3 live forward usable is a time-dependent monitoring gate — not a short-term development KPI."
)


@dataclass(frozen=True)
class WeeklyObservationReportV1:
    report_date: str
    cycle: WeeklyUsObservationResult
    portfolio_readiness: dict[str, Any]
    p10_hints: dict[str, Any]
    risk_veto_summary: dict[str, Any]
    observation_path: str | None
    observation_only: bool = True
    live_http: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "report_date": self.report_date,
            "observation_only": self.observation_only,
            "live_http": self.live_http,
            "observation_path": self.observation_path,
            "portfolio_readiness": self.portfolio_readiness,
            "p10_hints": self.p10_hints,
            "risk_veto_summary": self.risk_veto_summary,
            "p3_monitoring_gate": self.p3_monitoring_gate(),
        }

    def p3_monitoring_gate(self) -> dict[str, Any]:
        hints = self.p10_hints
        readiness = self.portfolio_readiness
        p3_sum = readiness.get("p3_us_forward_summary") or {}
        matched = int(
            hints.get("forward_matched")
            or p3_sum.get("matched_normal")
            or 0
        )
        needed = int(
            p3_sum.get("samples_needed_for_usable")
            or max(0, THIN_SAMPLE_THRESHOLD - matched)
        )
        return {
            "headline": P3_MONITORING_GATE_HEADLINE,
            "status": "immature_monitoring",
            "matched_normal": matched,
            "thin_threshold": THIN_SAMPLE_THRESHOLD,
            "samples_needed_for_usable": needed,
            "p3_sample_quality": hints.get("forward_p3_sample_quality")
            or readiness.get("p3_sample_quality_status"),
            "portfolio_readiness_note": (
                "Portfolio observation milestones (P0–P2) are evaluated independently; "
                "P3 live forward usable maturity does not block Weekly Observation Report v1."
            ),
            "historical_backfill": "deferred — not in scope for v1 completion",
        }


def _resolve_observation_path(*, path_base: Path) -> Path | None:
    candidates = (
        OUTPUTS_DIR / "observation_log" / "observation_log.jsonl",
        path_base / "outputs" / "observation_log" / "observation_log.jsonl",
        path_base / "observation_log" / "observation_log.jsonl",
    )
    return next((p for p in candidates if p.is_file()), None)


def build_weekly_observation_report_v1(
    *,
    path_base: Path | None = None,
    report_date: str | None = None,
) -> WeeklyObservationReportV1:
    """Cache-only weekly observation report v1 (no writes, no HTTP)."""

    root = path_base or ROOT_DIR
    obs_path = _resolve_observation_path(path_base=root)
    cycle = run_weekly_us_observation_cycle(
        path_base=root,
        manifest_out=None,
        write_observation_log=False,
        include_peer_sync=True,
    )
    portfolio_readiness = evaluate_portfolio_readiness(
        path_base=root,
        observation_path=obs_path,
    )
    p10_hints = build_post_refresh_hints_light(
        path_base=root,
        observation_path=obs_path,
    )
    risk_veto_summary = summarize_risk_veto_observation_log(obs_path) if obs_path else {
        "status": "missing",
        "headline": "observation_log missing — veto summary unavailable",
        "veto_triggered_rows": 0,
    }
    return WeeklyObservationReportV1(
        report_date=report_date or date.today().isoformat(),
        cycle=cycle,
        portfolio_readiness=portfolio_readiness,
        p10_hints=p10_hints,
        risk_veto_summary=risk_veto_summary,
        observation_path=str(obs_path) if obs_path else None,
    )


def _format_portfolio_observation_section(readiness: dict[str, Any]) -> list[str]:
    exposure = readiness.get("portfolio_exposure_by_signal_veto") or {}
    lines = [
        "## Portfolio observation",
        "",
        f"- shadow_positions: {exposure.get('shadow_position_count', 0)}",
        f"- symbols_with_signal_context: {exposure.get('symbols_with_signal_context', 0)}",
        f"- human_accepted_percent: {readiness.get('state_percent_human_accepted')}",
        f"- rubric_tier: {readiness.get('accepted_tier')} ({readiness.get('accepted_tier_label', '')})",
    ]
    for ms in readiness.get("milestones") or []:
        if isinstance(ms, dict) and ms.get("id"):
            lines.append(f"- {ms['id']}: {ms.get('status')} — {ms.get('detail', '')}")
    p3_prog = readiness.get("p3_forward_progress") or {}
    if p3_prog.get("progress_label"):
        lines.append(f"- portfolio_p3_forward: {p3_prog.get('progress_label')}")
    return lines


def _format_p10_gap_section(hints: dict[str, Any]) -> list[str]:
    tier1 = hints.get("tier1_missing") or []
    lines = [
        "## P10 gap (cache / tier-1; gated refresh)",
        "",
        f"- tier_1_missing_count: {len(tier1)}",
    ]
    if tier1:
        preview = ", ".join(str(s) for s in tier1[:8])
        if len(tier1) > 8:
            preview += f" … +{len(tier1) - 8} more"
        lines.append(f"- tier_1_missing_preview: {preview}")
    stale = hints.get("stale_skip_by_symbol") or []
    if stale:
        stale_syms: list[str] = []
        for item in stale:
            if isinstance(item, dict):
                sym = item.get("symbol")
                if sym:
                    stale_syms.append(str(sym))
            else:
                stale_syms.append(str(item))
        if stale_syms:
            lines.append(f"- stale_skip_symbols: {', '.join(stale_syms[:8])}")
    lines.append(f"- stale_skip_count: {hints.get('stale_skip_count', 0)}")
    lines.append(
        "- note: P10 tier-1 cache refresh requires human chat approval (docs/162); no live HTTP in v1 report."
    )
    return lines


def _format_p3_monitoring_section(report: WeeklyObservationReportV1) -> list[str]:
    gate = report.p3_monitoring_gate()
    lines = [
        "## P3 live forward usable (time-dependent monitoring gate)",
        "",
        f"- **{gate['headline']}**",
        f"- status: `{gate['status']}` (immature but monitoring — not a coding completion blocker)",
        f"- matched_normal: {gate['matched_normal']}/{gate['thin_threshold']} "
        f"({gate.get('p3_sample_quality') or 'unknown'})",
        f"- samples_needed_for_usable: {gate['samples_needed_for_usable']}",
        f"- portfolio_readiness: {gate['portfolio_readiness_note']}",
        f"- historical_backfill: {gate['historical_backfill']}",
    ]
    return lines


def _format_next_human_actions(report: WeeklyObservationReportV1) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()

    def _add(action: str) -> None:
        key = action.strip()
        if key and key not in seen:
            seen.add(key)
            actions.append(key)

    for item in report.p10_hints.get("recommended_actions") or []:
        _add(str(item))
    preflight = report.cycle.p3_path_preflight or {}
    for step in preflight.get("next_steps") or []:
        _add(str(step))
    l1 = report.portfolio_readiness.get("p3_l1_write_gate") or {}
    if l1.get("next_action"):
        _add(str(l1["next_action"]))
    obs = report.cycle.observation_log or {}
    for item in obs.get("research_checklist") or []:
        if isinstance(item, dict):
            action = item.get("next_action") or item.get("reason")
            sym = item.get("symbol") or ""
            if action:
                _add(f"[{item.get('category', 'research')}] {sym}: {action}".strip(": "))
    if not actions:
        actions.append(
            "No gated actions pending — continue weekly dry-run monitoring "
            "(weekly-observation-report-v1)."
        )
    lines = ["## Next human actions", ""]
    for action in actions[:12]:
        lines.append(f"- {action}")
    if len(actions) > 12:
        lines.append(f"- … +{len(actions) - 12} more (see observation-health / p3-path-to-usable)")
    return lines


def format_weekly_observation_report_v1_markdown(
    report: WeeklyObservationReportV1,
    *,
    path_base: Path | None = None,
) -> str:
    """Single-page markdown for MERGE/STOP human judgment."""

    root = path_base or ROOT_DIR
    q = report.cycle.quality
    o = report.cycle.observation_log or {}
    base = format_weekly_us_observation_markdown(report.cycle, path_base=root)
    header = [
        "# Weekly Observation Report v1",
        "",
        "Observation only — not buy/sell advice.",
        f"Report date: **{report.report_date}**",
        "",
        "## Executive summary",
        "",
        f"- US signals ok: **{q.get('signals_ok', 0)}/{q.get('symbol_count', 0)}** · "
        f"veto triggered (cache batch): **{q.get('veto_triggered_count', 0)}**",
        f"- observation_log us_signal_rows: **{o.get('us_signal_rows', 0)}** · "
        f"repeat symbols: **{len(o.get('repeat_signal_symbols') or [])}**",
        f"- P3 matched_normal: **{report.p3_monitoring_gate()['matched_normal']}/{THIN_SAMPLE_THRESHOLD}** "
        f"(monitoring; not short-term dev KPI)",
        "",
        "---",
        "",
    ]
    veto_md = format_risk_veto_observation_summary_markdown(report.risk_veto_summary)
    sections = [
        "\n".join(header),
        base.replace("# Weekly US observation (cache-only)", "## US signals (cache-only cycle)", 1),
        veto_md,
        "\n".join(_format_portfolio_observation_section(report.portfolio_readiness)),
        "\n".join(_format_p10_gap_section(report.p10_hints)),
        "\n".join(_format_p3_monitoring_section(report)),
        "\n".join(_format_next_human_actions(report)),
        "\n".join(
            [
                "## Report command",
                "",
                "- `.venv/bin/python -m invis_alpha_os.cli.main weekly-observation-report-v1`",
            ]
        ),
    ]
    return "\n\n".join(sections) + "\n"


def format_weekly_observation_report_v1_json(report: WeeklyObservationReportV1) -> str:
    import json

    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
