"""Tests for ops-smoke strict reason taxonomy."""

from __future__ import annotations

from invis_alpha_os.product.ops_smoke_report import OpsSmokeCheck, OpsSmokeReport
from invis_alpha_os.product.ops_smoke_taxonomy import classify_ops_smoke_strict


def _report(*checks: OpsSmokeCheck) -> OpsSmokeReport:
    return OpsSmokeReport(
        checks=list(checks),
        observation_health={},
        peer_sync_pairs=0,
        portfolio_positions=0,
        manifest_entries=1,
        signals_ok=1,
        signals_total=1,
        next_commands=[],
    )


def test_taxonomy_pass_all_ok() -> None:
    tax = classify_ops_smoke_strict(_report(OpsSmokeCheck("peer_sync_report", "ok", "pairs=1")))
    assert tax["taxonomy"] == "PASS"
    assert tax["strict_exit_hint"] == 0


def test_taxonomy_expected_blocked_repeat_and_stale() -> None:
    tax = classify_ops_smoke_strict(
        _report(
            OpsSmokeCheck(
                "observation_health",
                "warn",
                "us_signal_rows=10 parse_errors=0 repeat_signals=5 forward_stale_cache=1",
            )
        )
    )
    assert tax["taxonomy"] == "EXPECTED_BLOCKED"
    assert "repeat_signals" in tax["reasons"]
    assert "forward_stale_cache" in tax["reasons"]


def test_taxonomy_regression_on_fail() -> None:
    tax = classify_ops_smoke_strict(
        _report(OpsSmokeCheck("watchlist_manifest", "fail", "entries=0 missing_cache=0"))
    )
    assert tax["taxonomy"] == "REGRESSION"
    assert "zero_manifest_entries" in tax["reasons"]
