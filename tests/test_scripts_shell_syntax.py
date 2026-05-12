"""DevOps scripts: trivial bash -n parse check."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = [
    "scripts/env_doctor.sh",
    "scripts/daily_check.sh",
    "scripts/jquants_smoke.sh",
    "scripts/post_push_check.sh",
    "scripts/safe_commit_push.sh",
]


@pytest.mark.parametrize("rel", _SCRIPTS)
def test_shell_scripts_parse(rel: str) -> None:
    path = ROOT / rel
    assert path.is_file(), path
    # bash -n: syntax-only (no rm in these scripts).
    import subprocess

    r = subprocess.run(["bash", "-n", str(path)], check=False, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr or r.stdout

