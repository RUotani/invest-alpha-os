"""Opt-in US observation usefulness section for daily/weekly reports (cache-only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from invis_alpha_os.config.paths import ROOT_DIR
from invis_alpha_os.product.us_forward_return_validation import (
    compute_us_forward_returns,
    forward_validation_next_commands,
)
from invis_alpha_os.product.us_universe_expansion import build_us_universe_expansion_report
from invis_alpha_os.product.weekly_us_observation import build_enriched_us_observation_summary


def build_us_observation_usefulness_payload(*, path_base: Path | None = None) -> dict[str, Any]:
    """Aggregate observation_log summary, forward validation, expansion gaps (read-only)."""

    root = path_base or ROOT_DIR
    obs_path = root / "outputs" / "observation_log" / "observation_log.jsonl"
    cache_dir = root / "outputs" / "market_data" / "us_daily_bars"
    obs_summary = build_enriched_us_observation_summary(
        obs_path,
        path_base=root,
        cache_dir=cache_dir if cache_dir.is_dir() else None,
    )
    forward: dict[str, Any] | None = None
    if obs_path.is_file() and obs_summary.get("us_signal_rows", 0) > 0:
        try:
            forward = compute_us_forward_returns(
                observation_path=obs_path,
                cache_dir=cache_dir if cache_dir.is_dir() else None,
                path_base=root,
            )
        except (FileNotFoundError, ValueError):
            forward = None
    expansion = build_us_universe_expansion_report(
        path_base=root,
        tier="1",
        missing_only=True,
    )
    return {
        "observation_summary": obs_summary,
        "forward_validation": forward,
        "expansion_tier1_missing": expansion,
        "observation_only": True,
    }


def render_us_observation_summary_markdown(*, path_base: Path | None = None) -> str:
    payload = build_us_observation_usefulness_payload(path_base=path_base)
    lines = [
        "## US observation usefulness (cache-only)",
        "",
        "Observe and review only — not buy/sell advice.",
        "",
    ]
    obs = payload.get("observation_summary") or {}
    if obs.get("status") == "missing":
        lines.append("- observation_log: missing")
        lines.append("- next: run weekly-us-observation with --write-observation-log when ready")
        for cmd in forward_validation_next_commands():
            lines.append(f"- `{cmd}`")
    else:
        lines.append(f"- us_signal_rows: {obs.get('us_signal_rows')}")
        lines.append(f"- signal aging avg/max (days): {obs.get('signal_aging_days_avg')} / {obs.get('signal_aging_days_max')}")
        repeat = obs.get("repeat_signal_symbols") or []
        lines.append(f"- repeat symbols: {', '.join(repeat) if repeat else '(none)'}")
        weekly = obs.get("weekly_trend") or {}
        if weekly.get("status"):
            lines.append(f"- weekly_trend: {weekly.get('status')} (delta={weekly.get('delta')})")
        checklist = obs.get("research_checklist") or []
        if checklist:
            lines.append("")
            lines.append("### Research checklist")
            for item in checklist:
                if isinstance(item, dict):
                    sym = item.get("symbol") or "—"
                    lines.append(
                        f"- [{item.get('category')}] {sym}: {item.get('reason')} → {item.get('next_action')}"
                    )
                else:
                    lines.append(f"- {item}")

    fwd = payload.get("forward_validation")
    if fwd:
        sq = fwd.get("sample_quality") or {}
        lines.extend(
            [
                "",
                "### Forward validation summary",
                f"- sample quality: {sq.get('status')} ({sq.get('reason')})",
                f"- matched rows: {fwd.get('rows_matched')}",
                f"- interpretation: {sq.get('interpretation', '')}",
            ]
        )
        if sq.get("status") in {"empty", "thin"}:
            lines.append(f"- needed_more_samples: {sq.get('needed_more_samples')}")
        veto = fwd.get("veto_at_t") or {}
        lines.append(f"- veto-at-t: {veto.get('status')}")
        gb = (fwd.get("quality_buckets") or {}).get("global") or {}
        for h in fwd.get("horizons") or []:
            b = gb.get(str(h)) or {}
            if b.get("count"):
                lines.append(
                    f"- {h}d hit_rate_positive: {b.get('hit_rate_positive')} (n={b.get('count')})"
                )
    else:
        lines.extend(["", "### Forward validation summary", "- skipped (no observation_log rows)"])

    exp = payload.get("expansion_tier1_missing") or {}
    tier1 = exp.get("tier_1_missing_refresh_order") or exp.get("next_gated_refresh_order") or []
    if tier1:
        lines.extend(["", "### US expansion tier-1 missing cache (review order)", ""])
        for sym in tier1[:12]:
            lines.append(f"- {sym}")
        if len(tier1) > 12:
            lines.append(f"- … and {len(tier1) - 12} more (see us-universe-expansion-plan)")
    lines.append("")
    return "\n".join(lines)
