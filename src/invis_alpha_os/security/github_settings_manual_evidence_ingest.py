"""Ingest human-filled GitHub settings manual evidence JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from invis_alpha_os.security.github_settings_manual_evidence_template import MANUAL_CHECK_IDS

MANUAL_CHECK_STATUS_VALUES: frozenset[str] = frozenset(
    {
        "not_checked",
        "checked_pass",
        "checked_fail",
        "not_available_on_plan",
        "not_applicable",
    }
)


@dataclass(frozen=True)
class ManualEvidenceSummary:
    manual_checks_total: int
    manual_checks_passed: int
    manual_checks_failed: int
    manual_checks_not_checked: int
    manual_checks_not_available_on_plan: int
    manual_checks_not_applicable: int
    invalid_status_count: int
    loaded: bool
    source_path: str | None
    validation_errors: tuple[str, ...]


def _empty_summary(*, source_path: str | None = None) -> ManualEvidenceSummary:
    return ManualEvidenceSummary(
        manual_checks_total=0,
        manual_checks_passed=0,
        manual_checks_failed=0,
        manual_checks_not_checked=0,
        manual_checks_not_available_on_plan=0,
        manual_checks_not_applicable=0,
        invalid_status_count=0,
        loaded=False,
        source_path=source_path,
        validation_errors=(),
    )


def ingest_github_settings_manual_evidence(path: Path) -> ManualEvidenceSummary:
    if not path.is_file():
        return _empty_summary()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ManualEvidenceSummary(
            manual_checks_total=0,
            manual_checks_passed=0,
            manual_checks_failed=0,
            manual_checks_not_checked=0,
            manual_checks_not_available_on_plan=0,
            manual_checks_not_applicable=0,
            invalid_status_count=1,
            loaded=False,
            source_path=str(path),
            validation_errors=(f"invalid_json:{exc.__class__.__name__}",),
        )

    checks = payload.get("checks")
    if not isinstance(checks, list):
        return ManualEvidenceSummary(
            manual_checks_total=0,
            manual_checks_passed=0,
            manual_checks_failed=0,
            manual_checks_not_checked=0,
            manual_checks_not_available_on_plan=0,
            manual_checks_not_applicable=0,
            invalid_status_count=1,
            loaded=False,
            source_path=str(path),
            validation_errors=("missing_checks_array",),
        )

    passed = failed = not_checked = not_available = not_applicable = invalid = 0
    errors: list[str] = []
    for index, item in enumerate(checks):
        if not isinstance(item, dict):
            invalid += 1
            errors.append(f"check_{index}_not_object")
            continue
        status = str(item.get("manual_check_status", "not_checked"))
        if status not in MANUAL_CHECK_STATUS_VALUES:
            invalid += 1
            errors.append(f"invalid_status:{item.get('id', index)}={status}")
            continue
        if status == "checked_pass":
            passed += 1
        elif status == "checked_fail":
            failed += 1
        elif status == "not_checked":
            not_checked += 1
        elif status == "not_available_on_plan":
            not_available += 1
        elif status == "not_applicable":
            not_applicable += 1

    total = passed + failed + not_checked + not_available + not_applicable
    if total == 0 and not invalid:
        total = len(MANUAL_CHECK_IDS)

    return ManualEvidenceSummary(
        manual_checks_total=total,
        manual_checks_passed=passed,
        manual_checks_failed=failed,
        manual_checks_not_checked=not_checked,
        manual_checks_not_available_on_plan=not_available,
        manual_checks_not_applicable=not_applicable,
        invalid_status_count=invalid,
        loaded=True,
        source_path=str(path),
        validation_errors=tuple(errors),
    )


def default_manual_evidence_path(*, repo_root: Path) -> Path:
    return repo_root / "outputs" / "security" / "latest" / "github_settings_manual_evidence_template.json"


def load_github_settings_manual_evidence(
    *,
    repo_root: Path,
    evidence_path: Path | None = None,
) -> ManualEvidenceSummary:
    path = evidence_path if evidence_path is not None else default_manual_evidence_path(repo_root=repo_root)
    return ingest_github_settings_manual_evidence(path)
