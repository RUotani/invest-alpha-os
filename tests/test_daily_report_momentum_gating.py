"""Main R0: optional momentum sections via market_data.yaml daily_report keys."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from invis_alpha_os.cli import main as cli_main
from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR
from invis_alpha_os.data.us_daily_bars_cache import save_us_daily_bars_cache
from invis_alpha_os.signals.momentum import load_bars_json_file
from invis_alpha_os.utils.date_utils import today_jst_iso

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]
_FIX_MSFT = REPO_ROOT / "tests" / "fixtures" / "us_daily_bars" / "MSFT.json"


def test_daily_report_section_flags_yaml_wiring(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_main, "CONFIG_DIR", tmp_path)
    (tmp_path / "market_data.yaml").write_text(
        "daily_report:\n"
        "  include_momentum_cache_only_section: false\n"
        "  include_momentum_mixed_section: true\n",
        encoding="utf-8",
    )
    assert cli_main._daily_report_momentum_sections_flags() == (False, True, False)

    (tmp_path / "market_data.yaml").write_text(
        "daily_report:\n"
        '  include_momentum_cache_only_section: "false"\n'
        '  include_momentum_mixed_section: "TRUE"\n',
        encoding="utf-8",
    )
    assert cli_main._daily_report_momentum_sections_flags() == (False, True, False)


def test_daily_report_us_gate_defaults_false(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli_main, "CONFIG_DIR", tmp_path)
    (tmp_path / "market_data.yaml").write_text("daily_report: {}\n", encoding="utf-8")
    assert cli_main._daily_report_momentum_sections_flags() == (True, True, False)


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


def _run_daily_with_gate(monkeypatch, tmp_path: Path, gate: tuple[bool, bool, bool]) -> str:
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
    body = _run_daily_with_gate(monkeypatch, tmp_path, (True, True, False))
    assert "## Momentum Signals — Cache Only" in body
    assert "## Momentum Signals — Mixed / System Validation" in body


def test_daily_omits_mixed_when_disabled(monkeypatch, tmp_path: Path) -> None:
    body = _run_daily_with_gate(monkeypatch, tmp_path, (True, False, False))
    assert "## Momentum Signals — Cache Only" in body
    assert "## Momentum Signals — Mixed / System Validation" not in body


def test_daily_omits_cache_only_when_disabled(monkeypatch, tmp_path: Path) -> None:
    body = _run_daily_with_gate(monkeypatch, tmp_path, (False, True, False))
    assert "## Momentum Signals — Cache Only" not in body
    assert "## Momentum Signals — Mixed / System Validation" in body


def _minimal_us_bars_payload() -> list[dict]:
    bars = load_bars_json_file(_FIX_MSFT)
    return [dict(b) for b in bars[:30]]


def test_daily_yaml_gate_false_hides_us_section_even_with_us_cache(monkeypatch, tmp_path: Path) -> None:
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "watchlist.yaml").write_text((REPO_ROOT / "config" / "watchlist.yaml").read_text(encoding="utf-8"))

    md = yaml.safe_load((REPO_ROOT / "config" / "market_data.yaml").read_text(encoding="utf-8"))
    md.setdefault("daily_report", {})
    md["daily_report"]["include_us_momentum_cache_only_section"] = False
    (cfg_dir / "market_data.yaml").write_text(yaml.dump(md, allow_unicode=True, sort_keys=False))

    out_root = tmp_path / "outputs"
    monkeypatch.setattr(cli_main, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", out_root)
    monkeypatch.setattr("invis_alpha_os.data.us_daily_bars_cache.OUTPUTS_DIR", out_root)
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-01-01")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2025-12-31")

    save_us_daily_bars_cache(
        "MSFT",
        _minimal_us_bars_payload(),
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-09T12:00:00+00:00",
    )

    import urllib.request

    def _boom(*_a, **_k):
        raise AssertionError("daily US gate test must not use HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = runner.invoke(app, ["daily"])

    assert r.exit_code == 0, r.stdout + r.stderr
    body = (out_root / "reports" / "daily" / f"{today_jst_iso()}.md").read_text(encoding="utf-8")
    assert "## Momentum Signals — US Cache Only" not in body


def test_daily_yaml_gate_true_includes_us_section_when_cache_exists(monkeypatch, tmp_path: Path) -> None:
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    (cfg_dir / "watchlist.yaml").write_text((REPO_ROOT / "config" / "watchlist.yaml").read_text(encoding="utf-8"))

    md = yaml.safe_load((REPO_ROOT / "config" / "market_data.yaml").read_text(encoding="utf-8"))
    md.setdefault("daily_report", {})
    md["daily_report"]["include_us_momentum_cache_only_section"] = True
    (cfg_dir / "market_data.yaml").write_text(yaml.dump(md, allow_unicode=True, sort_keys=False))

    out_root = tmp_path / "outputs"
    monkeypatch.setattr(cli_main, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(cli_main, "OUTPUTS_DIR", out_root)
    monkeypatch.setattr("invis_alpha_os.data.us_daily_bars_cache.OUTPUTS_DIR", out_root)
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_FROM", "2024-01-01")
    monkeypatch.setenv("JQUANTS_DATA_AVAILABLE_TO", "2025-12-31")

    save_us_daily_bars_cache(
        "MSFT",
        _minimal_us_bars_payload(),
        asset_class="us_equity",
        source="local_fixture",
        fetched_at="2026-05-09T12:00:05+00:00",
    )

    import urllib.request

    def _boom(*_a, **_k):
        raise AssertionError("daily US gate-on test must not use HTTP")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    r = runner.invoke(app, ["daily"])

    assert r.exit_code == 0, r.stdout + r.stderr
    body = (out_root / "reports" / "daily" / f"{today_jst_iso()}.md").read_text(encoding="utf-8")
    slice_us = body.split("## Momentum Signals — US Cache Only", maxsplit=1)
    assert len(slice_us) == 2
    head = "## Momentum Signals — US Cache Only" + slice_us[1][:2500]
    assert "**Bars source:** `cache` — **US**" in head
    assert "| MSFT |" in body
