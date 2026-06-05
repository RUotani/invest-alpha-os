"""Weekly candidate brief scheduler shell script smoke."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_weekly_candidate_brief.sh"
TPL = REPO / "ops/launchd/com.invest-alpha-os.weekly-candidate-brief.plist.template"


def test_run_weekly_candidate_brief_script_bash_syntax() -> None:
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_weekly_launchd_template_placeholders_exist() -> None:
    text = TPL.read_text(encoding="utf-8")
    assert "__REPO_ROOT__" in text
    assert "__LOG_DIR__" in text
    assert "<key>Weekday</key>" in text
    assert "<integer>7</integer>" in text
    assert "Asia/Tokyo" in text


def test_weekly_script_generates_markdown_and_copy_outputs() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "--format markdown" in text
    assert "--format copy" in text
    assert "--format json" in text
    assert "weekly_candidate_brief_v0_1.md" in text
    assert "weekly_candidate_brief_copy.md" in text
    assert "weekly_candidate_brief.json" in text
    assert "weekly-candidate-brief-email" in text


def test_weekly_script_writes_v104_status_without_workflow_or_send_actions() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "weekly_artifact_status_schema_v104" in text
    assert "--email-text" in text
    assert "--email-html" in text
    assert "--email-eml" in text
    assert "--json-report" in text
    assert "GITHUB_EVENT_NAME" not in text
    assert "workflow_dispatch" not in text
    assert "--send-test" not in text
