from __future__ import annotations

from invis_alpha_os.discovery.early_discovery_score import (
    EarlyDiscoveryInputs,
    evaluate_early_discovery_score,
)


def test_insufficient_nullable_inputs_do_not_invent_score() -> None:
    result = evaluate_early_discovery_score(EarlyDiscoveryInputs(theme_phase="early"))

    assert result.score is None
    assert "recent_return" in result.missing
    assert "volume_inflection" in result.missing
    assert "fixture_only_not_performance_evidence" in result.reasons


def test_low_to_rising_fixture_gets_score_but_remains_uncalibrated() -> None:
    result = evaluate_early_discovery_score(
        EarlyDiscoveryInputs(
            theme_phase="acceleration",
            recent_return=0.08,
            ma_deviation=0.04,
            volume_inflection=0.35,
            rs_acceleration=0.02,
            portfolio_cash_ratio=0.20,
            single_stock_ratio=0.12,
        )
    )

    assert result.score is not None and result.score > 0.0
    assert result.missing == ()
    assert result.blocked_by == ()
    assert "weights_uncalibrated" in result.reasons
    assert "relative_strength_improving" in result.reasons


def test_cash_below_15_percent_blocks_new_risk_allowance() -> None:
    result = evaluate_early_discovery_score(
        EarlyDiscoveryInputs(
            theme_phase="early",
            recent_return=0.08,
            ma_deviation=0.04,
            volume_inflection=0.35,
            rs_acceleration=0.02,
            portfolio_cash_ratio=0.117,
            single_stock_ratio=0.12,
        )
    )

    assert result.score is not None
    assert "portfolio_cash_gate" in result.blocked_by


def test_285a_like_hard_overheat_is_blocked_not_early_discovery() -> None:
    result = evaluate_early_discovery_score(
        EarlyDiscoveryInputs(
            theme_phase="acceleration",
            recent_return=0.732,
            ma_deviation=0.45,
            volume_inflection=0.80,
            rs_acceleration=0.04,
            portfolio_cash_ratio=0.20,
            single_stock_ratio=0.12,
        )
    )

    assert result.score is not None
    assert "hard_overheat" in result.blocked_by


def test_non_early_theme_phase_is_explicitly_blocked() -> None:
    result = evaluate_early_discovery_score(
        EarlyDiscoveryInputs(
            theme_phase="overheat",
            recent_return=0.10,
            ma_deviation=0.05,
            volume_inflection=0.20,
            rs_acceleration=0.01,
        )
    )

    assert "theme_phase_not_early_or_acceleration" in result.blocked_by


def test_flat_rs_and_volume_do_not_meet_early_discovery_definition() -> None:
    result = evaluate_early_discovery_score(
        EarlyDiscoveryInputs(
            theme_phase="early",
            recent_return=0.05,
            ma_deviation=0.02,
            volume_inflection=0.0,
            rs_acceleration=0.0,
        )
    )

    assert "volume_not_inflecting" in result.blocked_by
    assert "relative_strength_not_improving" in result.blocked_by
