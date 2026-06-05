"""Fixture-only weekly artifact schema contract (v101 + v104)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping

from invis_alpha_os.product.scheduled_run_observation_readiness_v101 import (
    build_weekly_candidate_brief_scheduled_observation_checklist_v101,
    validate_fixture_artifact_texts_for_scheduled_observation_v101,
)
from invis_alpha_os.product.weekly_artifact_status_schema_v104 import (
    validate_weekly_artifact_status_v104,
)


@dataclass(frozen=True)
class WeeklyArtifactSchemaContractResult:
    ready: bool
    v101_ready: bool
    v104_valid: bool
    v104_issues: tuple[str, ...]
    v101_issue_count: int
    checked_paths: tuple[str, ...]


def validate_weekly_artifact_schema_contract(
    artifact_texts: Mapping[str, str],
    *,
    require_json_report: bool = True,
) -> WeeklyArtifactSchemaContractResult:
    checklist = build_weekly_candidate_brief_scheduled_observation_checklist_v101()
    texts = dict(artifact_texts)
    if not require_json_report and "weekly_candidate_brief.json" not in texts:
        pass
    v101 = validate_fixture_artifact_texts_for_scheduled_observation_v101(texts, checklist)
    v104_issues: tuple[str, ...] = ()
    v104_valid = False
    status_text = texts.get("status.json")
    if status_text:
        try:
            payload = json.loads(status_text)
            if isinstance(payload, Mapping):
                v104_issues = validate_weekly_artifact_status_v104(payload)
                v104_valid = not v104_issues
        except json.JSONDecodeError:
            v104_issues = ("invalid_json",)
    else:
        v104_issues = ("status.json:missing",)
    json_missing = require_json_report and "weekly_candidate_brief.json" not in texts
    v101_ready = v101.is_ready and not json_missing
    ready = v101_ready and v104_valid
    return WeeklyArtifactSchemaContractResult(
        ready=ready,
        v101_ready=v101_ready,
        v104_valid=v104_valid,
        v104_issues=v104_issues,
        v101_issue_count=len(v101.issues),
        checked_paths=v101.checked_paths,
    )
