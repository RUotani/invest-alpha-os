"""Main R0: optional momentum sections via market_data.yaml daily_report keys."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli import main as cli_main
from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.utils.date_utils import today_jst_iso

runner = CliRunner()


def test_daily_report_section_flags_yaml_wiring(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_main, "CONFIG_DIR", tmp_path)
    (tmp_path / "market_data.yaml").write_text(
        "daily_report:\n"
        "  include_momentum_cache_only_section: false\n"
        "  include_momentum_mixed_section: true\n",
        encoding="utf-8",
    )
    assert cli_main._daily_report_momentum_sections_flags() == (False, True)

    (tmp_path / "market_data.yaml").write_text(
        "daily_report:\n"
        '  include_momentum_cache_only_section: "false"\n'
        '  include_momentum_mixed_section: "TRUE"\n',
        encoding="utf-8",
    )
    assert cli_main._daily_report_momentum_sections_flags() == (False, True)


def test_daily_blank_line_before_momentum_when_jq_watchlist_suppressed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(cli_main, "_jquants_report_settings", lambda: {"include_watchlist_bars_check": False})
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-01-01")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2025-12-31")

    r = runner.invoke(app, ["daily"])
    assert r.exit_code == 0, r.stdout + r.stderr
    body = (OUTPUTS_DIR / "reports" / "daily" / f"{today_jst_iso()}.md").read_text(encoding="utf-8")
    assert "## J-Quants Watchlist Bars Check" not in body
    assert "\n\n## Momentum Signals — Cache Only" in body


def _run_daily_with_gate(monkeypatch, tmp_path: Path, gate: tuple[bool, bool]) -> str:
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-01-01")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2025-12-31")
    monkeypatch.setattr(
        "invis_alpha_os.cli.main._daily_report_momentum_sections_flags",
        lambda: gate,
    )
    r = runner.invoke(app, ["daily"])
    assert r.exit_code == 0, r.stdout + r.stderr
    path = OUTPUTS_DIR / "reports" / "daily" / f"{today_jst_iso()}.md"
    return path.read_text(encoding="utf-8")


def test_daily_includes_both_momentum_sections_by_gate_default_style(monkeypatch, tmp_path: Path) -> None:
    body = _run_daily_with_gate(monkeypatch, tmp_path, (True, True))
    assert "## Momentum Signals — Cache Only" in body
    assert "## Momentum Signals — Mixed / System Validation" in body


def test_daily_omits_mixed_when_disabled(monkeypatch, tmp_path: Path) -> None:
    body = _run_daily_with_gate(monkeypatch, tmp_path, (True, False))
    assert "## Momentum Signals — Cache Only" in body
    assert "## Momentum Signals — Mixed / System Validation" not in body


def test_daily_omits_cache_only_when_disabled(monkeypatch, tmp_path: Path) -> None:
    body = _run_daily_with_gate(monkeypatch, tmp_path, (False, True))
    assert "## Momentum Signals — Cache Only" not in body
    assert "## Momentum Signals — Mixed / System Validation" in body
