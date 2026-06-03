from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "weekly_candidate_brief.yml"
DECISION_PATH = ROOT / "docs" / "decisions" / "2026-06-03_temporary_scheduled_run_advance_v102.md"


def test_v102_workflow_keeps_normal_schedule_and_adds_temporary_observation_cron() -> None:
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert '- cron: "0 22 * * 5"' in workflow
    assert '- cron: "0 22 3 6 *"' in workflow
    assert "2026-06-04 07:00 JST = 2026-06-03 22:00 UTC" in workflow
    assert "Remove after v86 scheduled run observation completes." in workflow


def test_v102_decision_records_revert_requirement_and_safety_boundaries() -> None:
    decision = DECISION_PATH.read_text(encoding="utf-8")

    assert 'cron: "0 22 3 6 *"' in decision
    assert "2026-06-04 07:30 JST" in decision
    assert "must be removed after the v86 scheduled run observation completes" in decision
    assert "manual workflow_dispatch: not approved / not executed" in decision
    assert "cache write: not approved / not executed" in decision
    assert "actual refresh/import or manual actual import: not approved / not executed" in decision
    assert "broker API, broker login, or raw broker export parsing: not approved / not executed" in decision
    assert "raw Excel direct parsing: not approved / not executed" in decision
    assert "trading action, order placement, auto-trading, or real email: not approved / not executed" in decision
