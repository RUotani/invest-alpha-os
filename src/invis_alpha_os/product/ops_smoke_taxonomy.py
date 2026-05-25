"""Ops-smoke --strict reason taxonomy (read-only; observation only)."""

from __future__ import annotations

from typing import Any, Protocol


class _OpsSmokeCheckLike(Protocol):
    name: str
    status: str
    detail: str


class _OpsSmokeReportLike(Protocol):
    checks: list[_OpsSmokeCheckLike]

    @property
    def all_ok(self) -> bool: ...

EXPECTED_WARN_REASONS = frozenset(
    {
        "repeat_signals",
        "forward_stale_cache",
        "missing_cache_symbols",
        "tier1_cache_gaps",
        "peer_sync_forward_thin",
        "stale_repeat_flags",
    }
)
REGRESSION_REASONS = frozenset({"json_parse_errors", "signal_quality_fail", "zero_manifest_entries"})


def _warn_reasons_from_check(check: _OpsSmokeCheckLike) -> list[str]:
    reasons: list[str] = []
    if check.name == "observation_health":
        if "repeat_signals=" in check.detail:
            m = check.detail.split("repeat_signals=", 1)[-1].split()[0]
            if m.isdigit() and int(m) > 0:
                reasons.append("repeat_signals")
        if "forward_stale_cache=1" in check.detail:
            reasons.append("forward_stale_cache")
        if "tier1_gaps=" in check.detail:
            part = check.detail.split("tier1_gaps=", 1)[-1].split()[0]
            if part.isdigit() and int(part) > 0:
                reasons.append("tier1_cache_gaps")
        if "peer_sync_forward_thin=1" in check.detail:
            reasons.append("peer_sync_forward_thin")
        if "stale_repeat_flags=" in check.detail:
            part = check.detail.split("stale_repeat_flags=", 1)[-1].split()[0]
            if part.isdigit() and int(part) > 0:
                reasons.append("stale_repeat_flags")
        if "parse_errors=" in check.detail:
            part = check.detail.split("parse_errors=", 1)[-1].split()[0]
            if part.isdigit() and int(part) > 0:
                reasons.append("json_parse_errors")
    elif check.name == "watchlist_manifest" and check.status == "warn":
        reasons.append("missing_cache_symbols")
    elif check.name == "peer_map_config" and check.status == "warn":
        reasons.append("peer_map_config_missing")
    return reasons


def _fail_reasons_from_check(check: _OpsSmokeCheckLike) -> list[str]:
    if check.name == "watchlist_manifest":
        return ["zero_manifest_entries"]
    if check.name == "signal_quality_snapshot":
        return ["signal_quality_fail"]
    return [f"{check.name}_fail"]


def classify_ops_smoke_strict(report: _OpsSmokeReportLike) -> dict[str, Any]:
    """Classify strict gate: PASS / EXPECTED_BLOCKED / REGRESSION."""

    fail_checks = [c for c in report.checks if c.status == "fail"]
    warn_checks = [c for c in report.checks if c.status == "warn"]

    reasons: list[str] = []
    for c in fail_checks:
        reasons.extend(_fail_reasons_from_check(c))
    for c in warn_checks:
        reasons.extend(_warn_reasons_from_check(c))

    deduped = list(dict.fromkeys(reasons))
    regression_hits = [r for r in deduped if r in REGRESSION_REASONS or r.endswith("_fail")]
    expected_hits = [r for r in deduped if r in EXPECTED_WARN_REASONS]

    if report.all_ok:
        taxonomy = "PASS"
        exit_hint = 0
    elif fail_checks or regression_hits:
        taxonomy = "REGRESSION"
        exit_hint = 2
    elif deduped and all(r in EXPECTED_WARN_REASONS for r in deduped):
        taxonomy = "EXPECTED_BLOCKED"
        exit_hint = 2
    elif deduped:
        taxonomy = "REGRESSION"
        exit_hint = 2
    else:
        taxonomy = "EXPECTED_BLOCKED"
        exit_hint = 2

    return {
        "taxonomy": taxonomy,
        "strict_exit_hint": exit_hint,
        "reasons": deduped,
        "expected_reasons": expected_hits,
        "regression_reasons": regression_hits,
        "fail_checks": [c.name for c in fail_checks],
        "warn_checks": [c.name for c in warn_checks],
        "interpretation": _interpretation(taxonomy, deduped),
        "observation_only": True,
    }


def format_strict_taxonomy_stderr_line(report: _OpsSmokeReportLike) -> str:
    """One-line stderr summary for validate ops-smoke --strict."""

    tax = classify_ops_smoke_strict(report)
    reasons = tax.get("reasons") or []
    reason_part = ",".join(reasons) if reasons else "none"
    return (
        f"ops-smoke --strict: taxonomy={tax.get('taxonomy')} "
        f"exit={tax.get('strict_exit_hint')} reasons=[{reason_part}]"
    )


def _interpretation(taxonomy: str, reasons: list[str]) -> str:
    if taxonomy == "PASS":
        return "All checks ok; strict gate passes."
    if taxonomy == "EXPECTED_BLOCKED":
        joined = ", ".join(reasons) if reasons else "known warn"
        return f"Strict exit 2 with expected blocked reasons only ({joined})."
    joined = ", ".join(reasons) if reasons else "unknown"
    return f"Strict gate regression suspected ({joined})."
