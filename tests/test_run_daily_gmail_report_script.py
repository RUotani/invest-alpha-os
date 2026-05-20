"""R6.19-B: daily Gmail report shell script smoke."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_daily_gmail_report.sh"


def test_run_daily_gmail_report_script_bash_syntax() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_launchd_template_placeholders_exist() -> None:
    tpl = (REPO / "ops/launchd/com.invest-alpha-os.daily-gmail-report.plist.template").read_text(
        encoding="utf-8"
    )
    assert "__REPO_ROOT__" in tpl
    assert "__LOG_DIR__" in tpl
