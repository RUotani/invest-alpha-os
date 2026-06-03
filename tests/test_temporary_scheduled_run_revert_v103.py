from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "weekly_candidate_brief.yml"
DECISION_PATH = ROOT / "docs" / "decisions" / "2026-06-04_remove_temporary_scheduled_run_cron_v103.md"


def test_v103_removes_temporary_cron_and_keeps_normal_weekly_schedule() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert '- cron: "0 22 * * 5"' in workflow
    assert '- cron: "0 22 3 6 *"' not in workflow
    assert "Temporary v102 observation advance" not in workflow
    assert "Remove after v86 scheduled run observation completes." not in workflow
    assert "workflow_dispatch:" in workflow


def test_v103_decision_records_observation_not_seen_and_safety_boundaries() -> None:
    decision = DECISION_PATH.read_text(encoding="utf-8")

    assert "scheduled run not observed" in decision
    assert "0 22 3 6 *" in decision
    assert "0 22 * * 5" in decision
    assert "manual workflow_dispatch: not executed" in decision
    assert "provider live HTTP or market-data live fetch: not executed" in decision
    assert "cache write: not executed" in decision
    assert "actual import: not executed" in decision
    assert "broker API or raw Excel direct parsing: not executed" in decision
    assert "env/secret display: not executed" in decision
    assert "trading action or real email: not executed" in decision
