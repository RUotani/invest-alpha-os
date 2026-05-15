"""R6.12-E: US signals dry-run opt-in on daily report CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli import main as cli_main
from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR, ROOT_DIR
from invis_alpha_os.reports.us_signals_opt_in import append_us_signals_dry_run_section
from invis_alpha_os.utils.date_utils import today_jst_iso

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]
_VALID_MANIFEST = REPO_ROOT / "tests/fixtures/us_equities/us_cache_signals_batch_minimal.json"


def _daily_body(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *extra_args: str) -> str:
    monkeypatch.setattr(cli_main, "_jquants_report_settings", lambda: {"include_watchlist_bars_check": False})
    monkeypatch.setattr(
        "invis_alpha_os.cli.main._daily_report_momentum_sections_flags",
        lambda: (False, False, False),
    )
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    r = runner.invoke(app, ["daily", *extra_args])
    assert r.exit_code == 0, r.stdout + r.stderr
    return (OUTPUTS_DIR / "reports" / "daily" / f"{today_jst_iso()}.md").read_text(encoding="utf-8")


def test_daily_without_manifest_has_no_us_signals_dry_run_section(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    body = _daily_body(monkeypatch, tmp_path)
    assert "US Signals Dry Run" not in body


def test_daily_default_output_unchanged_when_flag_omitted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first = _daily_body(monkeypatch, tmp_path)
    second = _daily_body(monkeypatch, tmp_path)
    assert first == second
    assert "### US Signals Dry Run (opt-in)" not in first


def test_daily_with_valid_manifest_appends_opt_in_section(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    rel = _VALID_MANIFEST.relative_to(REPO_ROOT)
    body = _daily_body(monkeypatch, tmp_path, "--us-signals-dry-run-manifest", str(rel))
    assert "### US Signals Dry Run (opt-in)" in body
    assert "| MSFT |" in body
    assert "**live_http**: false" in body


def test_daily_with_invalid_manifest_does_not_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bad = tmp_path / "bad_manifest.json"
    bad.write_text("{not json", encoding="utf-8")
    body = _daily_body(monkeypatch, tmp_path, "--us-signals-dry-run-manifest", str(bad))
    assert "### US Signals Dry Run (opt-in)" in body
    assert "manifest_invalid" in body
    assert "# Daily Report" in body


def test_append_helper_invalid_manifest_short_notice() -> None:
    out = append_us_signals_dry_run_section(
        "# Daily Report\n",
        "/no/such/manifest.json",
        path_base=ROOT_DIR,
    )
    assert "manifest_invalid" in out
    assert "**live_http**: false" in out


def test_append_helper_valid_manifest_multi_symbol_rows() -> None:
    out = append_us_signals_dry_run_section(
        "base\n",
        _VALID_MANIFEST,
        path_base=ROOT_DIR,
    )
    assert out.startswith("base\n\n### US Signals Dry Run (opt-in)")
    assert out.count("| MSFT |") >= 2
