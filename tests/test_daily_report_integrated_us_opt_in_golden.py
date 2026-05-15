"""R6.13-A: JQ watchlist + momentum gates + US opt-in heading order."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli import main as cli_main
from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]
_VALID_MANIFEST = REPO_ROOT / "tests/fixtures/us_equities/us_cache_signals_batch_minimal.json"


def _isolated_config_dir(tmp_base: Path) -> Path:
    """Copy bundled ``*.yaml`` so momentum / veto paths resolve (no reliance on cwd)."""

    cfg = tmp_base / "repo_cfg"
    cfg.mkdir(parents=True)
    for p in (REPO_ROOT / "config").glob("*.yaml"):
        shutil.copy(p, cfg / p.name)
    return cfg


def _patch_integrated_context(monkeypatch: pytest.MonkeyPatch, cfg_dir: Path) -> None:
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-01-01")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2025-12-31")
    monkeypatch.setattr(cli_main, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("invis_alpha_os.config.paths.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", REPO_ROOT)
    monkeypatch.setattr("invis_alpha_os.cli.main.today_jst_iso", lambda: "2031-07-15")
    monkeypatch.setattr(
        cli_main,
        "_jquants_report_settings",
        lambda: {"include_watchlist_bars_check": True},
    )
    monkeypatch.setattr(
        "invis_alpha_os.cli.main._daily_report_momentum_sections_flags",
        lambda: (True, True, False),
    )


def test_integrated_heading_order_jq_momentum_then_us_opt_in_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg_dir = _isolated_config_dir(tmp_path)
    (cfg_dir / "watchlist.yaml").write_text('jp_watchlist:\n  - "7203"\n', encoding="utf-8")
    _patch_integrated_context(monkeypatch, cfg_dir)

    manifest_rel = str(_VALID_MANIFEST.relative_to(REPO_ROOT))
    r = runner.invoke(app, ["daily", "--us-signals-dry-run-manifest", manifest_rel])
    assert r.exit_code == 0, r.stdout + r.stderr

    body = (OUTPUTS_DIR / "reports" / "daily" / "2031-07-15.md").read_text(encoding="utf-8")

    ix_jq = body.index("## J-Quants Watchlist Bars Check")
    ix_c = body.index("## Momentum Signals — Cache Only")
    ix_m = body.index("## Momentum Signals — Mixed / System Validation")
    ix_us = body.index("### US Signals Dry Run (opt-in)")
    assert ix_jq < ix_c < ix_m < ix_us
    assert "Appended via `--us-signals-dry-run-manifest`" in body
    assert "| MSFT |" in body


def test_integrated_without_manifest_omits_us_opt_in_but_keeps_jq_and_momentum(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg_dir = _isolated_config_dir(tmp_path)
    (cfg_dir / "watchlist.yaml").write_text('jp_watchlist:\n  - "7203"\n', encoding="utf-8")
    _patch_integrated_context(monkeypatch, cfg_dir)

    r = runner.invoke(app, ["daily"])
    assert r.exit_code == 0, r.stdout + r.stderr

    body = (OUTPUTS_DIR / "reports" / "daily" / "2031-07-15.md").read_text(encoding="utf-8")
    assert "### US Signals Dry Run (opt-in)" not in body
    assert "## J-Quants Watchlist Bars Check" in body
    assert "## Momentum Signals — Cache Only" in body
    assert "## Momentum Signals — Mixed / System Validation" in body
