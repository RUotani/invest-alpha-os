"""ops_write_json: local summary files (no secrets; default path gitignored)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_ops_write_json_pytest_mode(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "ops_write_json.py"
    r = subprocess.run(
        [sys.executable, str(script), "--mode", "pytest", "--pytest-exit", "0", "--output-dir", str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    s = json.loads((tmp_path / "latest_ops_summary.json").read_text(encoding="utf-8"))
    v = json.loads((tmp_path / "latest_verdict.json").read_text(encoding="utf-8"))
    assert s["schema_version"] == 1
    assert s["mode"] == "pytest"
    assert s["pytest_exit_code"] == 0
    assert s["pytest_passed"] is True
    assert s["live_http_performed"] is False
    assert v["verdict"] == "pass"
