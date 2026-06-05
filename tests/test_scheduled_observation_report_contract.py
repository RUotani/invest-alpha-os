from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OBSERVATION = REPO / "reports-private" / "scheduled_observation" / "scheduled_run_observation_20260606.md"

REQUIRED_SECTIONS = (
    "## Observation Summary",
    "## Classification",
    "## Findings",
    "## Missing / Gaps",
    "## Next Actions",
    "## Safety Summary",
)

REQUIRED_PHRASES = (
    "workflow_dispatch",
    "OBSERVATION_PENDING_SCHEDULED_RUN_NOT_VISIBLE",
    "PENDING",
)


def test_scheduled_observation_report_has_required_sections() -> None:
    text = OBSERVATION.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in text


def test_scheduled_observation_report_documents_workflow_dispatch_not_executed() -> None:
    text = OBSERVATION.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text
    assert "workflow 変更: **なし**" in text
