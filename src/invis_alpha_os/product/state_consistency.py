"""Read-only consistency checker for STATE.md."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path


@dataclass(frozen=True)
class StateConsistencyIssue:
    code: str
    severity: str
    message: str


@dataclass(frozen=True)
class StateConsistencyResult:
    path: str
    ok: bool
    latest_verified_main: str | None
    expected_main: str | None
    issues: tuple[StateConsistencyIssue, ...]
    safety_notes: tuple[str, ...]


_LATEST_MAIN_RE = re.compile(r"\*\*latest verified main\*\*: `(?P<sha>[0-9a-f]{7,40})`")

_REQUIRED_MARKERS: tuple[tuple[str, str], ...] = (
    ("weekly_primary_system", "Weekly Candidate Brief"),
    ("scheduled_observation_pending", "2026-06-06 07:30 JST"),
    ("workflow_change_unapproved", "workflow変更は未承認"),
    ("manual_dispatch_unapproved", "manual workflow_dispatch 未承認"),
    ("provider_live_http_unapproved", "provider live HTTP 未承認"),
    ("market_data_live_fetch_unapproved", "market-data live fetch 未承認"),
    ("cache_write_no_go", "cache write: **NO-GO**"),
    ("actual_import_no_go", "actual refresh/import / manual actual import: **NO-GO**"),
    ("broker_api_no_go", "broker API / broker login: **NO-GO**"),
    ("raw_excel_no_go", "raw Excel direct parsing: **NO-GO**"),
    ("env_secret_forbidden", "env/secret 表示禁止"),
    ("real_email_no_go", "real email send: **NO-GO**"),
    ("trading_action_no_go", "trading action / order placement / 自動売買: **NO-GO**"),
    ("generated_artifact_policy", "生成物であり、原則コミットしない"),
)


def _extract_latest_verified_main(text: str) -> str | None:
    match = _LATEST_MAIN_RE.search(text)
    if match:
        return match.group("sha")
    return None


def check_state_consistency(
    path: Path,
    *,
    expected_main: str | None = None,
    strict_latest_main: bool = False,
) -> StateConsistencyResult:
    text = path.read_text(encoding="utf-8")
    issues: list[StateConsistencyIssue] = []
    latest = _extract_latest_verified_main(text)
    if latest is None:
        issues.append(
            StateConsistencyIssue(
                code="latest_verified_main_missing",
                severity="ERROR",
                message="STATE.md must include a latest verified main SHA",
            )
        )
    if expected_main and latest and latest != expected_main:
        issues.append(
            StateConsistencyIssue(
                code="latest_verified_main_mismatch",
                severity="ERROR" if strict_latest_main else "WARN",
                message=f"latest verified main {latest} != expected {expected_main}",
            )
        )
    for code, marker in _REQUIRED_MARKERS:
        if marker not in text:
            issues.append(
                StateConsistencyIssue(
                    code=f"missing_{code}",
                    severity="ERROR",
                    message=f"required STATE marker is missing: {marker}",
                )
            )
    ok = not any(issue.severity == "ERROR" for issue in issues)
    return StateConsistencyResult(
        path=str(path),
        ok=ok,
        latest_verified_main=latest,
        expected_main=expected_main,
        issues=tuple(issues),
        safety_notes=(
            "read-only STATE.md consistency check",
            "STATE.md content is not modified by this checker",
            "no workflow change / workflow_dispatch / live HTTP / cache write / actual import",
            "no broker API / raw Excel parsing / env secret display / trading action / real email send",
        ),
    )


def format_state_consistency_json(result: StateConsistencyResult) -> str:
    payload = {
        "path": result.path,
        "ok": result.ok,
        "latest_verified_main": result.latest_verified_main,
        "expected_main": result.expected_main,
        "issues": [issue.__dict__ for issue in result.issues],
        "safety_notes": list(result.safety_notes),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_state_consistency_markdown(result: StateConsistencyResult) -> str:
    lines = [
        "# STATE.md Consistency Check",
        "",
        f"- path: `{result.path}`",
        f"- ok: {str(result.ok).lower()}",
        f"- latest_verified_main: {result.latest_verified_main or 'missing'}",
        f"- expected_main: {result.expected_main or 'not supplied'}",
        "",
        "## Issues",
    ]
    if result.issues:
        lines.extend(f"- [{issue.severity}] {issue.code}: {issue.message}" for issue in result.issues)
    else:
        lines.append("- none")
    lines.extend(["", "## Safety Notes"])
    lines.extend(f"- {note}" for note in result.safety_notes)
    lines.append("")
    return "\n".join(lines)
