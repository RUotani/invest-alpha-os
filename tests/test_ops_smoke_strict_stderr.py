"""Tests for ops-smoke --strict stderr taxonomy one-liner."""

from __future__ import annotations

from invis_alpha_os.product.ops_smoke_report import OpsSmokeCheck, OpsSmokeReport
from invis_alpha_os.product.ops_smoke_taxonomy import format_strict_taxonomy_stderr_line


def test_format_strict_taxonomy_stderr_line_expected_blocked() -> None:
    report = OpsSmokeReport(
        checks=[
            OpsSmokeCheck(
                "observation_health",
                "warn",
                "us_signal_rows=10 parse_errors=0 repeat_signals=5 forward_stale_cache=1",
            )
        ],
        observation_health={},
        peer_sync_pairs=0,
        portfolio_positions=0,
        manifest_entries=1,
        signals_ok=1,
        signals_total=1,
        next_commands=[],
    )
    line = format_strict_taxonomy_stderr_line(report)
    assert "taxonomy=EXPECTED_BLOCKED" in line
    assert "exit=2" in line
    assert "repeat_signals" in line


def test_format_strict_taxonomy_stderr_line_pass() -> None:
    report = OpsSmokeReport(
        checks=[OpsSmokeCheck("peer_sync_report", "ok", "pairs=1")],
        observation_health={},
        peer_sync_pairs=1,
        portfolio_positions=0,
        manifest_entries=1,
        signals_ok=1,
        signals_total=1,
        next_commands=[],
    )
    line = format_strict_taxonomy_stderr_line(report)
    assert "taxonomy=PASS" in line
    assert "exit=0" in line
