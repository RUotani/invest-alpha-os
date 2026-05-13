"""Sanity-check ops shell scripts (bash -n only; no live HTTP)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = [
    _ROOT / "scripts" / "jq_watchlist_bars_cache_preview.sh",
    _ROOT / "scripts" / "jq_watchlist_bars_cache_live.sh",
    _ROOT / "scripts" / "jq_refresh_workflow.sh",
    _ROOT / "scripts" / "daily_momentum_check.sh",
    _ROOT / "scripts" / "agent_final_check.sh",
    _ROOT / "scripts" / "agent_daily_momentum_check_no_env.sh",
]


@pytest.mark.parametrize("path", _SCRIPTS, ids=lambda p: p.name)
def test_ops_scripts_bash_syntax(path: Path) -> None:
    assert path.is_file()
    subprocess.run(["bash", "-n", str(path)], check=True)
