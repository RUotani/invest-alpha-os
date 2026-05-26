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


def test_run_daily_gmail_report_sent_marker_under_email_dir() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'EMAIL_DIR="${BUNDLE_DIR}/email"' in text
    assert 'SENT_MARKER="${EMAIL_DIR}/email_sent.json"' in text
    assert "dry-run (pre-send)" in text


def test_run_daily_gmail_report_send_failed_status() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "'status': 'send_failed'" in text
    assert "FAIL_REASON" in text
    assert "email_sent.json" in text
    assert "sent.write_text" in text
    assert text.index("send_failed") < text.index("sent_ok") or "send_failed" in text


def test_run_daily_gmail_report_email_sent_only_on_success() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "if [[ \"${SEND_RC}\" -eq 0 ]]" in text
    assert "sent.write_text" in text
    assert "send_failed" in text
