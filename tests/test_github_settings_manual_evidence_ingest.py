from __future__ import annotations

import json
from pathlib import Path

import pytest

from invis_alpha_os.security.github_settings_manual_evidence_ingest import (
    ingest_github_settings_manual_evidence,
)
from invis_alpha_os.security.security_dashboard import _resolve_grade


def _write_template(path: Path, statuses: list[str]) -> None:
    checks = [
        {"id": f"check_{index}", "manual_check_status": status, "notes": "", "checked_at": None}
        for index, status in enumerate(statuses)
    ]
    path.write_text(json.dumps({"checks": checks}), encoding="utf-8")


def test_ingest_missing_template() -> None:
    summary = ingest_github_settings_manual_evidence(Path("/nonexistent/template.json"))
    assert summary.loaded is False
    assert summary.manual_checks_total == 0


def test_ingest_all_not_checked(tmp_path: Path) -> None:
    path = tmp_path / "template.json"
    _write_template(path, ["not_checked", "not_checked"])
    summary = ingest_github_settings_manual_evidence(path)
    assert summary.loaded is True
    assert summary.manual_checks_not_checked == 2
    assert summary.manual_checks_failed == 0


def test_ingest_all_checked_pass(tmp_path: Path) -> None:
    path = tmp_path / "template.json"
    _write_template(path, ["checked_pass", "not_applicable", "not_available_on_plan"])
    summary = ingest_github_settings_manual_evidence(path)
    assert summary.manual_checks_passed == 1
    assert summary.manual_checks_not_checked == 0


def test_ingest_checked_fail(tmp_path: Path) -> None:
    path = tmp_path / "template.json"
    _write_template(path, ["checked_fail"])
    summary = ingest_github_settings_manual_evidence(path)
    assert summary.manual_checks_failed == 1


def test_ingest_invalid_status(tmp_path: Path) -> None:
    path = tmp_path / "template.json"
    _write_template(path, ["bogus_status"])
    summary = ingest_github_settings_manual_evidence(path)
    assert summary.invalid_status_count == 1
    assert summary.validation_errors


def test_resolve_grade_with_all_pass_evidence() -> None:
    from invis_alpha_os.security.github_settings_manual_evidence_ingest import ManualEvidenceSummary

    evidence = ManualEvidenceSummary(
        manual_checks_total=2,
        manual_checks_passed=2,
        manual_checks_failed=0,
        manual_checks_not_checked=0,
        manual_checks_not_available_on_plan=0,
        manual_checks_not_applicable=0,
        invalid_status_count=0,
        loaded=True,
        source_path="template.json",
        validation_errors=(),
    )
    grade = _resolve_grade(
        leakage_status="pass",
        actions_status="pass",
        deps_status="pass",
        file_intake_status="not_run",
        manual_check_count=3,
        tracked_reports_count=1,
        retained_secret_hit_count=0,
        manual_evidence=evidence,
    )
    assert grade == "pass"


def test_resolve_grade_checked_fail_downgrades() -> None:
    from invis_alpha_os.security.github_settings_manual_evidence_ingest import ManualEvidenceSummary

    evidence = ManualEvidenceSummary(
        manual_checks_total=1,
        manual_checks_passed=0,
        manual_checks_failed=1,
        manual_checks_not_checked=0,
        manual_checks_not_available_on_plan=0,
        manual_checks_not_applicable=0,
        invalid_status_count=0,
        loaded=True,
        source_path="template.json",
        validation_errors=(),
    )
    grade = _resolve_grade(
        leakage_status="pass",
        actions_status="pass",
        deps_status="pass",
        file_intake_status="not_run",
        manual_check_count=0,
        tracked_reports_count=1,
        retained_secret_hit_count=0,
        manual_evidence=evidence,
    )
    assert grade == "review_required"
