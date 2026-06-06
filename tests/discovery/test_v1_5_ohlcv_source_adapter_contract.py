from __future__ import annotations

import ast
from pathlib import Path

from invis_alpha_os.discovery.early_discovery_score import evaluate_early_discovery_score
from invis_alpha_os.discovery.v1_5_ohlcv_source_adapter import (
    V15_READONLY_APPROVAL_PHRASE,
    FixtureV15OhlcvSourceAdapter,
    V15OhlcvAdapterMode,
    bars_from_closes_volumes,
    build_early_discovery_inputs_from_series,
    evaluate_v15_readonly_gate,
)


def _rising_fixture() -> tuple[object, object]:
    closes = [100.0 + index for index in range(30)]
    volumes = [100.0] * 25 + [200.0] * 5
    asset = bars_from_closes_volumes(symbol="TEST", market="US", closes=closes, volumes=volumes)
    benchmark = bars_from_closes_volumes(
        symbol="SPY",
        market="US",
        closes=[100.0] * 30,
        volumes=[1_000_000.0] * 30,
    )
    return asset, benchmark


def test_fixture_adapter_returns_series_without_network() -> None:
    asset, benchmark = _rising_fixture()
    adapter = FixtureV15OhlcvSourceAdapter({"TEST": asset, "SPY": benchmark})

    assert adapter.fetch_series("TEST", market="US") == asset
    assert adapter.fetch_series("TEST", market="JP") is None
    assert adapter.fetch_series("MISSING", market="US") is None
    assert adapter.health()["network"] == "disabled"


def test_readonly_gate_blocks_live_without_approval() -> None:
    blocked = evaluate_v15_readonly_gate(adapter_mode=V15OhlcvAdapterMode.LIVE_READ_ONLY)
    allowed_fixture = evaluate_v15_readonly_gate(adapter_mode=V15OhlcvAdapterMode.FIXTURE_ONLY)
    allowed_live = evaluate_v15_readonly_gate(
        adapter_mode=V15OhlcvAdapterMode.LIVE_READ_ONLY,
        allow_live_fetch=True,
        approval_phrase=V15_READONLY_APPROVAL_PHRASE,
    )

    assert blocked.allowed is False
    assert blocked.reason == "live_read_only_not_approved"
    assert allowed_fixture.allowed is True
    assert allowed_live.allowed is True


def test_build_inputs_and_score_from_fixture_series() -> None:
    asset, benchmark = _rising_fixture()
    inputs = build_early_discovery_inputs_from_series(
        asset,
        benchmark=benchmark,
        theme_phase="early",
        portfolio_cash_ratio=0.20,
        single_stock_ratio=0.10,
    )
    score = evaluate_early_discovery_score(inputs)

    assert inputs.recent_return is not None and inputs.recent_return > 0.0
    assert inputs.volume_inflection is not None and inputs.volume_inflection > 0.0
    assert inputs.rs_acceleration is not None and inputs.rs_acceleration > 0.0
    assert score.score is not None
    assert "fixture_only_not_performance_evidence" in score.reasons


def test_adapter_module_has_no_network_or_file_io_imports() -> None:
    source_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "invis_alpha_os"
        / "discovery"
        / "v1_5_ohlcv_source_adapter.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports.isdisjoint({"pathlib", "os", "requests", "urllib", "http", "socket", "pandas"})
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"open", "print"}
        for node in ast.walk(tree)
    )


def test_wrong_approval_phrase_blocks_live() -> None:
    result = evaluate_v15_readonly_gate(
        adapter_mode=V15OhlcvAdapterMode.LIVE_READ_ONLY,
        allow_live_fetch=True,
        approval_phrase="wrong phrase",
    )
    assert result.allowed is False
