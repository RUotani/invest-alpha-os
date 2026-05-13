"""Main Q0: Investment OS coverage map doc guardrails — no HTTP; doc + makefile hook only."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_DOC = ROOT / "docs" / "10_investment_os_coverage_map.md"
MAKEFILE = ROOT / "Makefile"

REQUIRED_SUBSTRINGS = (
    "Total Investment OS",
    "JP equities",
    "US equities",
    "gold",
    "bonds",
    "crypto",
    "portfolio",
    "subsystem progress",
    "total Investment OS progress",
    "momentum pipeline",
    "fundamentals",
    "Main R",
    "data fetching still not implemented",
)


def test_investment_os_coverage_markdown_exists_and_keywords() -> None:
    txt = COVERAGE_DOC.read_text(encoding="utf-8")
    for needle in REQUIRED_SUBSTRINGS:
        assert needle in txt, f"missing keyword: {needle!r}"


def test_makefile_defines_investment_os_coverage_target() -> None:
    mf = MAKEFILE.read_text(encoding="utf-8")
    assert "\ninvestment-os-coverage:" in mf or mf.startswith("investment-os-coverage:")
    assert "10_investment_os_coverage_map.md" in mf


def test_make_investment_os_coverage_runs_without_error() -> None:
    proc = subprocess.run(
        ["make", "investment-os-coverage"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Total Investment OS" in proc.stdout
    assert proc.stderr == ""
