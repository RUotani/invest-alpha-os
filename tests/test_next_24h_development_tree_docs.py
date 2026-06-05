from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN = REPO_ROOT / "docs" / "plans" / "2026-06-06_next_24h_development_tree.md"
DECISION = REPO_ROOT / "docs" / "decisions" / "2026-06-05_next_24h_development_tree_proposal.md"


def test_next_24h_plan_has_time_gated_observation_policy() -> None:
    text = PLAN.read_text()

    assert "2026-06-06 07:30 JST" in text
    assert "`NOT_YET_OBSERVABLE`" in text
    assert "`OBSERVABILITY_MISS`" in text
    assert "Manual dispatch, rerun, or workflow edits are not allowed" in text


def test_next_24h_plan_keeps_hard_gates_closed() -> None:
    text = PLAN.read_text()

    required_markers = [
        "workflow change or `.github/workflows` edit",
        "manual workflow_dispatch or rerun",
        "live HTTP / market-data live fetch",
        "cache write or cache directory creation",
        "actual refresh/import or manual import",
        "broker API, broker login, raw broker export parsing",
        "raw Excel direct parsing",
        "env/secret display",
        "trading action, order placement, automated trading",
        "real email send",
    ]

    for marker in required_markers:
        assert marker in text


def test_next_24h_decision_points_to_plan_and_human_approval_boundary() -> None:
    text = DECISION.read_text()

    assert "docs/plans/2026-06-06_next_24h_development_tree.md" in text
    assert "If a fix needs workflow changes" in text
    assert "require human approval" in text
