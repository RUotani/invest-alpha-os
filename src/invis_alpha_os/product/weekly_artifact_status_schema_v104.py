"""v104 weekly artifact status schema for scheduled-run observation."""

from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

SCHEMA_VERSION_V104 = "v104"
SOURCE_MODE_V104 = "observation_only_no_live_http"
EXPECTED_MARKERS_V104: tuple[str, ...] = (
    "Score / Veto",
    "Pipeline",
    "Sanitized / Manual Input",
    "User-Facing Input Review",
)
_SAFE_TRIGGER_ENV_KEYS: tuple[str, ...] = (
    "GITHUB_EVENT_NAME",
    "GITHUB_WORKFLOW",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_SHA",
    "GITHUB_REF",
)


def _optional_text(value: str | None) -> str | None:
    stripped = (value or "").strip()
    return stripped or None


def classify_trigger_event_v104(event_name: str | None) -> str:
    value = _optional_text(event_name)
    if value is None:
        return "local"
    if value in {"schedule", "workflow_dispatch"}:
        return value
    return "unknown"


def safe_trigger_metadata_from_env_v104(env: Mapping[str, str] | None = None) -> dict[str, str | None]:
    source = env if env is not None else os.environ
    safe = {key: _optional_text(source.get(key)) for key in _SAFE_TRIGGER_ENV_KEYS}
    return {
        "event_name": classify_trigger_event_v104(safe["GITHUB_EVENT_NAME"]),
        "workflow": safe["GITHUB_WORKFLOW"],
        "run_id": safe["GITHUB_RUN_ID"],
        "run_attempt": safe["GITHUB_RUN_ATTEMPT"],
        "sha": safe["GITHUB_SHA"],
        "ref": safe["GITHUB_REF"],
    }


def build_weekly_artifact_status_v104(
    *,
    report_date: str,
    full_report: str,
    copy_report: str,
    email_text: str,
    email_html: str,
    email_eml: str,
    status_file: str,
    json_report: str | None = None,
    completed_at: str | None = None,
    env: Mapping[str, str] | None = None,
    existing_paths: Sequence[str] | None = None,
) -> dict[str, object]:
    trigger = safe_trigger_metadata_from_env_v104(env)
    expected_paths = (full_report, copy_report, email_text, email_html, email_eml)
    present = set(existing_paths) if existing_paths is not None else {path for path in expected_paths if Path(path).is_file()}
    generation_complete = all(path in present for path in expected_paths)
    completed = completed_at or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": SCHEMA_VERSION_V104,
        "date": report_date,
        "status": "weekly_candidate_brief_generated",
        "full_report": full_report,
        "copy_report": copy_report,
        "completed_at": completed,
        "source_mode": SOURCE_MODE_V104,
        "dry_run": True,
        "trigger": trigger,
        "reports": {
            "full_report": full_report,
            "copy_report": copy_report,
            "json_report": json_report,
        },
        "email_preview": {
            "text": email_text,
            "html": email_html,
            "eml": email_eml,
            "gmail_send_attempted": False,
        },
        "observation": {
            "expected_markers": list(EXPECTED_MARKERS_V104),
            "artifact_generation_complete": generation_complete,
            "status_file": status_file,
        },
    }


def validate_weekly_artifact_status_v104(payload: Mapping[str, object]) -> tuple[str, ...]:
    issues: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION_V104:
        issues.append("schema_version")
    for key in ("date", "status", "full_report", "copy_report", "completed_at", "source_mode", "dry_run"):
        if key not in payload:
            issues.append(key)
    trigger = payload.get("trigger")
    if not isinstance(trigger, Mapping) or trigger.get("event_name") not in {
        "schedule",
        "workflow_dispatch",
        "local",
        "unknown",
    }:
        issues.append("trigger.event_name")
    reports = payload.get("reports")
    if not isinstance(reports, Mapping) or not reports.get("full_report") or not reports.get("copy_report"):
        issues.append("reports")
    email = payload.get("email_preview")
    if not isinstance(email, Mapping) or email.get("gmail_send_attempted") is not False:
        issues.append("email_preview.gmail_send_attempted")
    observation = payload.get("observation")
    if not isinstance(observation, Mapping) or "artifact_generation_complete" not in observation:
        issues.append("observation.artifact_generation_complete")
    return tuple(issues)


def write_weekly_artifact_status_v104(path: str, payload: Mapping[str, object]) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write v104 weekly artifact status JSON.")
    parser.add_argument("--status-file", required=True)
    parser.add_argument("--report-date", required=True)
    parser.add_argument("--full-report", required=True)
    parser.add_argument("--copy-report", required=True)
    parser.add_argument("--email-text", required=True)
    parser.add_argument("--email-html", required=True)
    parser.add_argument("--email-eml", required=True)
    parser.add_argument("--json-report")
    return parser


def main() -> int:
    args = _parser().parse_args()
    payload = build_weekly_artifact_status_v104(
        report_date=args.report_date,
        full_report=args.full_report,
        copy_report=args.copy_report,
        json_report=args.json_report,
        email_text=args.email_text,
        email_html=args.email_html,
        email_eml=args.email_eml,
        status_file=args.status_file,
    )
    issues = validate_weekly_artifact_status_v104(payload)
    if issues:
        raise ValueError(f"invalid v104 weekly artifact status: {', '.join(issues)}")
    write_weekly_artifact_status_v104(args.status_file, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
