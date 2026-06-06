from __future__ import annotations

import ast
from pathlib import Path

import pytest

from invis_alpha_os.discovery.price_volume_metrics import (
    compute_moving_average_deviation,
    compute_recent_return,
    compute_relative_strength_series,
    compute_rs_acceleration,
    compute_volume_inflection,
)


def test_insufficient_or_invalid_data_returns_none() -> None:
    assert compute_recent_return([100.0], 2) is None
    assert compute_moving_average_deviation([], 5) is None
    assert compute_volume_inflection([100.0] * 10) is None
    assert compute_recent_return([0.0, 100.0], 2) is None
    assert compute_rs_acceleration([100.0] * 10, [100.0] * 10) is None


def test_recent_return_and_moving_average_deviation() -> None:
    prices = [100.0, 105.0, 110.0]

    assert compute_recent_return(prices, 3) == pytest.approx(0.10)
    assert compute_moving_average_deviation(prices, 3) == pytest.approx(110.0 / 105.0 - 1.0)


def test_volume_inflection_detects_low_base_increase() -> None:
    volumes = [100.0] * 20 + [150.0] * 5

    assert compute_volume_inflection(volumes) == pytest.approx(0.50)


def test_rs_acceleration_distinguishes_flat_from_low_to_rising() -> None:
    benchmark = [100.0] * 25
    flat_asset = [200.0] * 25
    rising_asset = [100.0] * 20 + [100.0, 102.0, 105.0, 109.0, 114.0]

    assert compute_rs_acceleration(flat_asset, benchmark) == pytest.approx(0.0)
    assert compute_rs_acceleration(rising_asset, benchmark) > 0.0
    assert compute_relative_strength_series([100.0, 110.0], [100.0, 100.0]) == [1.0, 1.1]


def test_metric_module_has_no_network_or_file_io_imports() -> None:
    source_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "invis_alpha_os"
        / "discovery"
        / "price_volume_metrics.py"
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
