"""R6.13-B: Operator-facing smoke for US dry-run manifest opt-in (no product changes)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from invis_alpha_os.cli import main as cli_main
from invis_alpha_os.cli.main import app
from invis_alpha_os.config.paths import OUTPUTS_DIR

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]
_RUNBOOK_REL_MANIFEST = "tests/fixtures/us_equities/us_cache_signals_batch_minimal.json"


def _daily_body(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *extra_args: str) -> str:
    monkeypatch.setattr(cli_main, "_jquants_report_settings", lambda: {"include_watchlist_bars_check": False})
    monkeypatch.setattr(
        "invis_alpha_os.cli.main._daily_report_momentum_sections_flags",
        lambda: (False, False, False),
    )
    monkeypatch.setattr("invis_alpha_os.reports.jquants_watchlist_daily.ROOT_DIR", tmp_path)
    monkeypatch.chdir(REPO_ROOT)
    r = runner.invoke(app, ["daily", *extra_args])
    assert r.exit_code == 0, r.stdout + r.stderr
    return (OUTPUTS_DIR / "reports" / "daily" / f"{cli_main.today_jst_iso()}.md").read_text(encoding="utf-8")


def test_daily_help_documents_us_signals_dry_run_manifest_flag() -> None:
    """Prefer a real subprocess (`python -m ...`) — matches runbook / avoids CliRunner coupling."""

    env = os.environ.copy()
    pp = env.get("PYTHONPATH", "").strip(os.pathsep)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT / "src"), pp]).strip(os.pathsep)
    env.setdefault("NO_COLOR", "1")
    env["COLUMNS"] = "240"

    proc = subprocess.run(
        [sys.executable, "-m", "invis_alpha_os.cli.main", "daily", "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout + proc.stderr
    assert "--us-signals-dry-run-manifest" in out


def test_operational_invoke_from_repo_root_with_runbook_relative_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fixture path strings in docs/runbook resolve when cwd is repo root."""

    monkeypatch.setattr("invis_alpha_os.cli.main.today_jst_iso", lambda: "2031-07-15")

    body = _daily_body(monkeypatch, tmp_path, "--us-signals-dry-run-manifest", _RUNBOOK_REL_MANIFEST)
    assert "### US Signals Dry Run (opt-in)" in body
    assert "Appended via `--us-signals-dry-run-manifest`" in body
    assert "| MSFT |" in body


def test_operational_schema_invalid_manifest_exit_code_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Valid JSON but invalid manifest envelope ⇒ skip notice; daily still succeeds."""

    bad = tmp_path / "empty_entries.json"
    bad.write_text('{"schema_version": 1, "entries": []}', encoding="utf-8")
    body = _daily_body(monkeypatch, tmp_path, "--us-signals-dry-run-manifest", str(bad))
    assert "### US Signals Dry Run (opt-in)" in body
    assert "manifest_invalid" in body

